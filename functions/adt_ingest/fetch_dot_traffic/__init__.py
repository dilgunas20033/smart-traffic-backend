import os, logging, datetime, json, requests
from shared import get_clients, load_segment_map

# Expected env vars:
# FDOT_TRAFFIC_API_URL - base endpoint for FDOT traffic data (JSON)
# FDOT_API_KEY - optional, if the chosen API requires a key
# SEGMENT_MAP_CONTAINER - blob container holding segment_map.csv (default: raw)
# SEGMENT_MAP_BLOB - blob path (default: segment_map.csv)
# TRAFFIC_HISTORY_CONTAINER - container to append raw snapshots (default: raw)

RATE_LIMIT_SLEEP_SECONDS = 2


def fetch_fdot_json() -> list:
    base = os.environ.get("FDOT_TRAFFIC_API_URL")
    if not base:
        logging.error("FDOT_TRAFFIC_API_URL not set")
        return []
    headers = {}
    api_key = os.environ.get("FDOT_API_KEY")
    if api_key:
        headers['Authorization'] = f"Bearer {api_key}"
    try:
        resp = requests.get(base, headers=headers, timeout=15)
        if resp.status_code == 429:  # rate limit
            logging.warning("Rate limited; backing off")
            import time
            time.sleep(RATE_LIMIT_SLEEP_SECONDS)
            resp = requests.get(base, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Assume data is either a list of records or wrapped in a key
        if isinstance(data, dict):
            # Try common wrapper keys
            for k in ('records','data','items'):
                if k in data and isinstance(data[k], list):
                    return data[k]
            # Fallback: flatten values that are list
            flat = []
            for v in data.values():
                if isinstance(v, list):
                    flat.extend(v)
            return flat
        elif isinstance(data, list):
            return data
        else:
            logging.warning("Unexpected JSON shape from FDOT API")
            return []
    except Exception as e:
        logging.error(f"FDOT fetch failed: {e}")
        return []

def normalize_record(rec: dict) -> dict:
    # Adjust field names based on actual FDOT API once known.
    # Provide defensive defaults.
    return {
        'external_id': str(rec.get('segment_id') or rec.get('id') or rec.get('SegmentID') or ''),
        'avgSpeed': rec.get('speed') or rec.get('AverageSpeed'),
        'volume': rec.get('volume') or rec.get('Volume'),
        'timestamp': rec.get('timestamp') or rec.get('Timestamp') or datetime.datetime.utcnow().isoformat()
    }

def build_patch(norm: dict) -> list:
    ops = []
    if norm['avgSpeed'] is not None:
        try:
            ops.append({"op":"add","path":"/avgSpeed","value":float(norm['avgSpeed'])})
        except: pass
    if norm['volume'] is not None:
        try:
            ops.append({"op":"add","path":"/volume","value":float(norm['volume'])})
        except: pass
    ops.append({"op":"add","path":"/asOf","value":str(norm['timestamp'])})
    return ops

def write_history(blob_client, records: list):
    container = os.environ.get("TRAFFIC_HISTORY_CONTAINER", "raw")
    ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    name = f"history/traffic_{ts}.json"  # append-only snapshot
    try:
        blob_client.get_blob_client(container=container, blob=name).upload_blob(json.dumps(records), overwrite=False)
    except Exception as e:
        logging.warning(f"Failed writing history snapshot: {e}")

def main(myTimer) -> None:
    logging.info("Traffic timer trigger fired")
    adt, blob = get_clients()
    mapping = load_segment_map(blob)
    raw_records = fetch_fdot_json()
    normalized = [normalize_record(r) for r in raw_records]

    updated, skipped = 0, 0
    for norm in normalized:
        ext_id = norm['external_id']
        if not ext_id:
            skipped += 1
            continue
        twin_id = mapping.get(ext_id)
        if not twin_id:
            skipped += 1
            continue
        patch = build_patch(norm)
        if not patch:
            skipped += 1
            continue
        try:
            adt.update_digital_twin(twin_id, patch)
            updated += 1
        except Exception as e:
            logging.error(f"Failed patch twin {twin_id}: {e}")
            skipped += 1

    write_history(blob, normalized)
    logging.info(f"Traffic update complete. Updated={updated} Skipped={skipped} TotalRaw={len(raw_records)}")
