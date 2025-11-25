"""RoadSegment Twin Migration Script

Creates v2 twins for existing RoadSegment;1 twins by copying properties.
Existing twin IDs are preserved with a suffix (e.g., Segment_001 -> Segment_001_v2) to avoid collision.
Relationships are not automatically migrated; export and recreate as needed.

Usage (PowerShell):
    $env:ADT_ENDPOINT="https://<name>.api.<region>.digitaltwins.azure.net"
    python scripts/migrate_to_v2.py

Requires DefaultAzureCredential chain (Azure CLI login, Managed Identity, etc.)
"""
import os, logging
from azure.identity import DefaultAzureCredential
from azure.digitaltwins.core import DigitalTwinsClient

OLD_MODEL = "dtmi:fgcu:traffic:RoadSegment;1"
NEW_MODEL = os.environ.get("ROADSEGMENT_V2_ID", "dtmi:fgcu:traffic:RoadSegment;2")
SUFFIX = os.environ.get("ROADSEGMENT_V2_SUFFIX", "_v2")
DRY_RUN = os.environ.get("ROADSEGMENT_V2_DRY_RUN", "true").lower() == "true"

def main():
    endpoint = os.environ.get("ADT_ENDPOINT")
    if not endpoint:
        raise SystemExit("ADT_ENDPOINT not set")
    cred = DefaultAzureCredential()
    client = DigitalTwinsClient(endpoint, cred)

    query = f"SELECT * FROM digitaltwins WHERE IS_OF_MODEL('{OLD_MODEL}')"
    twins_to_migrate = list(client.query_twins(query))
    logging.info(f"Found {len(twins_to_migrate)} twins of model {OLD_MODEL}")

    migrated = 0
    for twin in twins_to_migrate:
        orig_id = twin.get("$dtId")
        new_id = f"{orig_id}{SUFFIX}"
        contents = {k: v for k, v in twin.items() if not k.startswith("$")}
        new_twin = {
            "$dtId": new_id,
            "$metadata": {"$model": NEW_MODEL},
            **contents
        }
        if DRY_RUN:
            logging.info(f"[DRY RUN] Would create new twin {new_id} from {orig_id}")
            continue
        try:
            client.upsert_digital_twin(new_id, new_twin)
            migrated += 1
        except Exception as e:
            logging.error(f"Failed to create twin {new_id}: {e}")

    logging.info(f"Migration complete. Migrated={migrated} DryRun={DRY_RUN}")

if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    main()