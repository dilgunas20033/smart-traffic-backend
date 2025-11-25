import os
from azure.storage.blob import BlobServiceClient

REQUIRED = [
    os.environ.get("SEGMENT_MAP_CONTAINER", "raw"),
    os.environ.get("TRAFFIC_HISTORY_CONTAINER", "raw"),
    os.environ.get("PREDICTION_CONTAINER", "predictions"),
    "seed",  # optional seed container
]

def main():
    conn = os.environ.get("STORAGE_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")
    if not conn:
        raise SystemExit("No STORAGE_CONNECTION_STRING or AzureWebJobsStorage found in environment.")
    svc = BlobServiceClient.from_connection_string(conn)
    created = []
    for name in REQUIRED:
        try:
            svc.create_container(name)
            created.append(name)
        except Exception:
            pass  # already exists or no permission
    print("Ensured containers exist:", ", ".join(REQUIRED))
    if created:
        print("Created new:", ", ".join(created))
    print("Listing containers:")
    for c in svc.list_containers():
        print(" -", c["name"])  # returns dict-like

if __name__ == "__main__":
    main()
