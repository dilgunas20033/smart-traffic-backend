import logging
import azure.functions as func
from shared import get_clients, read_csv

def upsert_twin(adt, twin):
    adt.upsert_digital_twin(twin["$dtId"], twin)

def upsert_patch(adt, twin_id, patch_ops):
    adt.update_digital_twin(twin_id, patch_ops)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Ingest start")
    adt, blob = get_clients()

    # 1) Seed segments
    try:
        seed_bytes = blob.get_blob_client("raw", "seed/seed_segments.json").download_blob().readall()
        import json
        seed = json.loads(seed_bytes)
        for twin in seed:
            upsert_twin(adt, twin)
    except Exception as e:
        logging.warning(f"No seed or failed to seed: {e}")

    # 2) Traffic metrics
    try:
        tdf = read_csv(blob, "raw", "traffic.csv")
        for _, r in tdf.iterrows():
            patch = [
                {"op":"add","path":"/avgSpeed","value":float(r["avgSpeed"])},
                {"op":"add","path":"/volume","value":float(r["volume"])},
                {"op":"add","path":"/asOf","value":str(r["asOf"])}
            ]
            upsert_patch(adt, r["segmentId"], patch)
    except Exception as e:
        logging.warning(f"Traffic load skipped: {e}")

    # 3) Pavement metrics
    try:
        pdf = read_csv(blob, "raw", "pavement.csv")
        for _, r in pdf.iterrows():
            patch = [
                {"op":"add","path":"/PCI","value":float(r["PCI"])},
                {"op":"add","path":"/IRI","value":float(r["IRI"])},
                {"op":"add","path":"/asOf","value":str(r["asOf"])}
            ]
            upsert_patch(adt, r["segmentId"], patch)
    except Exception as e:
        logging.warning(f"Pavement load skipped: {e}")

    return func.HttpResponse("Ingest done", status_code=200)
