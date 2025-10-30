import azure.functions as func, os, json
from azure.identity import DefaultAzureCredential
from azure.digitaltwins.core import DigitalTwinsClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    threshold = float(req.params.get("threshold", "0.7"))
    cred = DefaultAzureCredential()
    adt = DigitalTwinsClient(os.environ["ADT_ENDPOINT"], cred)
    query = """
    SELECT segment from DIGITALTWINS segment
    WHERE IS_OF_MODEL(segment, 'dtmi:fgcu:traffic:RoadSegment;1')
      AND segment.predictedCongestionIndex > @threshold
    """
    results = adt.query_twins(query, parameterized=True, parameters={"threshold": threshold})
    out = []
    for r in results:
        seg = r.get('segment') or r
        out.append({
            "segmentId": seg["$dtId"],
            "predictedAvgSpeed": seg.get("predictedAvgSpeed"),
            "predictedCongestionIndex": seg.get("predictedCongestionIndex"),
            "predictionHorizon": seg.get("predictionHorizon")
        })
    out = sorted(out, key=lambda x: (x["predictedCongestionIndex"] or 0), reverse=True)[:10]
    return func.HttpResponse(json.dumps(out), status_code=200, mimetype="application/json")
