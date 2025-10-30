import os, io
from azure.identity import DefaultAzureCredential
from azure.digitaltwins.core import DigitalTwinsClient
from azure.storage.blob import BlobServiceClient
import pandas as pd

def get_clients():
    cred = DefaultAzureCredential()
    adt = DigitalTwinsClient(os.environ["ADT_ENDPOINT"], cred)
    sa  = os.environ["STORAGE_ACCOUNT_NAME"]
    blob = BlobServiceClient(f"https://{sa}.blob.core.windows.net", credential=cred)
    return adt, blob

def read_csv(blob_client, container, name):
    b = blob_client.get_blob_client(container=container, blob=name).download_blob().readall()
    return pd.read_csv(io.BytesIO(b))
