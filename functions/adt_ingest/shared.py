import os, io, csv, logging
from azure.identity import DefaultAzureCredential
from azure.digitaltwins.core import DigitalTwinsClient
from azure.storage.blob import BlobServiceClient
import pandas as pd

def get_clients():
    cred = DefaultAzureCredential()
    adt = DigitalTwinsClient(os.environ["ADT_ENDPOINT"], cred)
    # Prefer explicit storage connection string if provided (easier local dev)
    conn = os.environ.get("STORAGE_CONNECTION_STRING")
    if conn:
        blob = BlobServiceClient.from_connection_string(conn)
    else:
        sa = os.environ["STORAGE_ACCOUNT_NAME"]
        blob = BlobServiceClient(f"https://{sa}.blob.core.windows.net", credential=cred)
    return adt, blob

def read_csv(blob_client, container, name):
    b = blob_client.get_blob_client(container=container, blob=name).download_blob().readall()
    return pd.read_csv(io.BytesIO(b))

def load_segment_map(blob_service):
    """Load external->twin segment mapping from blob CSV.

    Environment variables:
    SEGMENT_MAP_CONTAINER (default: raw)
    SEGMENT_MAP_BLOB (default: segment_map.csv)
    """
    container = os.environ.get("SEGMENT_MAP_CONTAINER", "raw")
    name = os.environ.get("SEGMENT_MAP_BLOB", "segment_map.csv")
    mapping = {}
    try:
        data = blob_service.get_blob_client(container=container, blob=name).download_blob().readall()
        f = io.StringIO(data.decode())
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#') or len(row) < 2:
                continue
            ext_id, twin_id = row[0].strip(), row[1].strip()
            if ext_id and twin_id:
                mapping[ext_id] = twin_id
    except Exception as e:
        logging.warning(f"Segment map not loaded: {e}")
    return mapping
