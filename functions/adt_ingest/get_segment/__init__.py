import azure.functions as func, os, json
from azure.identity import DefaultAzureCredential
from azure.digitaltwins.core import DigitalTwinsClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    seg_id = req.params.get("id")
    if not seg_id:
        return func.HttpResponse("Missing id", status_code=400)
    cred = DefaultAzureCredential()
    adt = DigitalTwinsClient(os.environ["ADT_ENDPOINT"], cred)
    twin = adt.get_digital_twin(seg_id)
    return func.HttpResponse(json.dumps(twin), status_code=200, mimetype="application/json")
