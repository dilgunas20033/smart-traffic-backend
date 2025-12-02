import azure.functions as func
import os, json
from shared import get_clients

def main(req: func.HttpRequest) -> func.HttpResponse:
    _, blob = get_clients()
    container = os.environ.get("TRAFFIC_HISTORY_CONTAINER", "raw")
    prefix = req.params.get('prefix') or 'incidents_'
    try:
        cc = blob.get_container_client(container)
        blobs = sorted([b.name for b in cc.list_blobs(name_starts_with=prefix)])
        if not blobs:
            return func.HttpResponse(json.dumps({"message":"no blobs"}), status_code=200, mimetype='application/json')
        latest = blobs[-1]
        data = cc.download_blob(latest).readall()
        return func.HttpResponse(data, status_code=200, mimetype='application/json')
    except Exception as e:
        return func.HttpResponse(json.dumps({"error":str(e)}), status_code=500, mimetype='application/json')
