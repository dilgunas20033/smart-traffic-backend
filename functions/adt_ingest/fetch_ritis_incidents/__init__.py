import logging
import os
import re
import json
from datetime import datetime, timezone
import azure.functions as func
import feedparser
import requests
from azure.digitaltwins.core import DigitalTwinsClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
from shared import load_segment_map, get_clients

# Regex patterns to extract fields from HTML description blocks
SEGMENT_ID_PATTERNS = [
    re.compile(r"Segment (?P<id>[A-Za-z0-9_-]+)"),
    re.compile(r"SEG(?P<id>[0-9]+)"),
    re.compile(r"SegmentID[:\s]+(?P<id>[A-Za-z0-9_-]+)")
]
COORD_RE = re.compile(r"(?P<lat>-?\d+\.\d+),(?P<lon>-?\d+\.\d+)")
LANE_STATUS_RE = re.compile(r"Lane Status:\s*(?P<affected>\d+)\s+out of\s+(?P<total>\d+)\s+lanes affected\s*(?P<impact>.*?)\s*\((?P<direction>[NSEW][B]?|[A-Za-z]+)\)", re.IGNORECASE)
LAST_UPDATE_RE = re.compile(r"Last Update Time:\s*(?P<dt>[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}[-+][0-9]{2}:[0-9]{2})")

def parse_segment_id(text: str):
    for pat in SEGMENT_ID_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group("id")
    return None

def parse_coordinates(text: str):
    return [
        {"lat": float(m.group("lat")), "lon": float(m.group("lon"))}
        for m in COORD_RE.finditer(text)
    ]

def parse_lane_status(text: str):
    m = LANE_STATUS_RE.search(text)
    if not m:
        return None
    return {
        "incidentAffectedLanes": int(m.group("affected")),
        "incidentTotalLanes": int(m.group("total")),
        "incidentLaneImpact": m.group("impact").strip(),
        "incidentDirection": m.group("direction").strip()
    }

def parse_last_update(text: str):
    m = LAST_UPDATE_RE.search(text)
    if not m:
        return None
    try:
        # Use raw string; ADT expects ISO 8601; convert if needed
        raw = m.group("dt")
        # Replace space with 'T' to approximate ISO 8601
        iso = raw.replace(" ", "T")
        return iso
    except Exception:
        return None

def fetch_authenticated_feed(url: str):
    email = os.environ.get("RITIS_EMAIL")
    password = os.environ.get("RITIS_PASSWORD")
    login_url = os.environ.get("RITIS_LOGIN_URL")

    if not email or not password or not login_url:
        # Fallback: unauthenticated direct fetch
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

    session = requests.Session()
    try:
        # Initial GET (capture cookies / tokens if any)
        session.get(login_url, timeout=30)
        # Attempt common form field names
        payload_variants = [
            {"username": email, "password": password},
            {"email": email, "password": password},
            {"user": email, "pass": password}
        ]
        logged_in = False
        for payload in payload_variants:
            try:
                r = session.post(login_url, data=payload, timeout=30)
                if r.status_code < 400 and ("logout" in r.text.lower() or "dashboard" in r.text.lower()):
                    logged_in = True
                    break
            except Exception:
                continue
        if not logged_in:
            logging.warning("Login heuristics did not confirm session; proceeding to fetch feed anyway.")
        feed_resp = session.get(url, timeout=30)
        feed_resp.raise_for_status()
        return feed_resp.text
    except Exception as ex:
        logging.error(f"Authenticated fetch failed: {ex}; falling back to direct.")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

def main(myTimer: func.TimerRequest) -> None:
    logging.info("RITIS incidents timer triggered")
    rss_url = os.environ.get("RITIS_RSS_URL")
    if not rss_url:
        logging.warning("RITIS_RSS_URL not set; skipping")
        return

    try:
        raw_feed = fetch_authenticated_feed(rss_url)
    except Exception as ex:
        logging.error(f"Failed to retrieve feed: {ex}")
        return

    feed = feedparser.parse(raw_feed)
    if feed.bozo:
        logging.error(f"Failed to parse feed: {feed.bozo_exception}")
        return

    try:
        client, blob_service = get_clients()
    except KeyError as e:
        logging.error(f"Missing required env var: {e}")
        return

    segment_map = load_segment_map(blob_service)

    incidents = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for entry in feed.entries:
        desc = entry.get("description", "") or ""
        title = entry.get("title", "") or ""
        segment_external_id = parse_segment_id(desc) or parse_segment_id(title)
        coords = parse_coordinates(desc)
        lane_data = parse_lane_status(desc) or {}
        incident_last_update = parse_last_update(desc)

        status = "active"
        lowered = desc.lower()
        if "scene is clear" in lowered or "all vehicles have departed" in lowered or "cleared" in lowered:
            status = "cleared"

        incident = {
            "title": title,
            "summary": desc[:500],
            "externalSegmentId": segment_external_id,
            "coordinates": coords,
            "status": status,
            "published": entry.get("published", None),
            "ingested": now_iso,
            **lane_data
        }
        if incident_last_update:
            incident["incidentLastUpdate"] = incident_last_update
        incidents.append(incident)

        if segment_external_id:
            twin_id = segment_map.get(segment_external_id) or map_external_to_twin(segment_external_id)
            if twin_id:
                patch_ops = [
                    {"op": "add", "path": "/status", "value": status},
                    {"op": "add", "path": "/lastSeen", "value": now_iso}
                ]
                # Attempt to include incident properties if model version supports them
                for prop in [
                    "incidentAffectedLanes","incidentTotalLanes","incidentLaneImpact","incidentDirection","incidentLastUpdate"
                ]:
                    if prop in incident:
                        patch_ops.append({"op": "add", "path": f"/{prop}", "value": incident[prop]})
                # Derive congestionIndex from lane closure ratio if available
                affected = incident.get("incidentAffectedLanes")
                total = incident.get("incidentTotalLanes")
                if isinstance(affected, int) and isinstance(total, int) and total > 0:
                    ratio = min(1.0, max(0.0, affected / total))
                    patch_ops.append({"op": "add", "path": "/congestionIndex", "value": ratio})
                    # Optionally mirror as predictedCongestionIndex until predictive model exists
                    patch_ops.append({"op": "add", "path": "/predictedCongestionIndex", "value": ratio})
                try:
                    client.update_digital_twin(twin_id, patch_ops)
                except ResourceNotFoundError:
                    logging.warning(f"Twin {twin_id} not found for incident {segment_external_id}")
                except Exception as ex:
                    logging.error(f"Patch failed {twin_id}: {ex}")

    # Archive snapshot
    try:
        history_container = os.environ.get("TRAFFIC_HISTORY_CONTAINER", "history")
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        # Ensure container exists
        try:
            blob_service.create_container(history_container)
        except Exception:
            pass
        blob_client = blob_service.get_blob_client(container=history_container, blob=f"incidents_{ts}.json")
        blob_client.upload_blob(json.dumps(incidents, indent=2), overwrite=True)
    except Exception as ex:
        logging.error(f"Failed to archive incidents: {ex}")

def map_external_to_twin(external_id: str) -> str:
    # TODO: Replace with CSV-based mapping using segment_map.csv
    return external_id
