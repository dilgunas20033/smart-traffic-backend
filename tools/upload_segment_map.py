import os, sys
from azure.storage.blob import BlobServiceClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/upload_segment_map.py path/to/segment_map.csv")
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)
    conn = os.environ.get("STORAGE_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")
    if not conn:
        print("No storage connection string in env (STORAGE_CONNECTION_STRING or AzureWebJobsStorage).")
        sys.exit(1)
    container = os.environ.get("SEGMENT_MAP_CONTAINER", "raw")
    svc = BlobServiceClient.from_connection_string(conn)
    try:
        svc.create_container(container)
    except Exception:
        pass
    blob_client = svc.get_blob_client(container, os.environ.get("SEGMENT_MAP_BLOB", "segment_map.csv"))
    with open(path, 'rb') as f:
        blob_client.upload_blob(f, overwrite=True)
    print(f"Uploaded mapping to container '{container}' as '{os.environ.get('SEGMENT_MAP_BLOB','segment_map.csv')}'.")

if __name__ == '__main__':
    main()
