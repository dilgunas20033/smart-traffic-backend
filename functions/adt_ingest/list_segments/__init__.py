import azure.functions as func, os, json
from azure.identity import DefaultAzureCredential
from azure.digitaltwins.core import DigitalTwinsClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        cred = DefaultAzureCredential()
        adt = DigitalTwinsClient(os.environ["ADT_ENDPOINT"], cred)
        # Basic query for all road segments
        query = """
        SELECT seg FROM DIGITALTWINS seg WHERE IS_OF_MODEL(seg, 'dtmi:fgcu:traffic:RoadSegment;1')
        """
        results = adt.query_twins(query)
        out = []
        for r in results:
            seg = r.get('seg') or r
            out.append({
                'segmentId': seg.get('$dtId'),
                'avgSpeed': seg.get('avgSpeed'),
                'volume': seg.get('volume'),
                'PCI': seg.get('PCI'),
                'IRI': seg.get('IRI'),
                'prediction': {
                    'predictedAvgSpeed': seg.get('predictedAvgSpeed'),
                    'predictedCongestionIndex': seg.get('predictedCongestionIndex')
                }
            })
        return func.HttpResponse(json.dumps(out), status_code=200, mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(f"Error: {e}", status_code=500)
