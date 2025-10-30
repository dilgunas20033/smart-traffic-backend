import logging
import azure.functions as func
import pandas as pd
from shared import get_clients
import io

def main(req: func.HttpRequest) -> func.HttpResponse:
    adt, blob = get_clients()
    try:
        b = blob.get_blob_client("raw", "predictions.csv").download_blob().readall()
        df = pd.read_csv(io.BytesIO(b))
        for _, r in df.iterrows():
            patch = [
                {"op":"add","path":"/predictedAvgSpeed","value":float(r["predictedAvgSpeed"])},
                {"op":"add","path":"/predictedCongestionIndex","value":float(r["predictedCongestionIndex"])},
                {"op":"add","path":"/predictionTimestamp","value":str(r["predictionTimestamp"])},
                {"op":"add","path":"/predictionHorizon","value":str(r["predictionHorizon"])}
            ]
            adt.update_digital_twin(r["segmentId"], patch)
    except Exception as e:
        logging.error(f"Prediction write failed: {e}")
        return func.HttpResponse("Error", status_code=500)
    return func.HttpResponse("Predictions written", status_code=200)
