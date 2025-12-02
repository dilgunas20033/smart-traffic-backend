import logging
import azure.functions as func
import pandas as pd
from shared import get_clients
import io, json

def main(req: func.HttpRequest) -> func.HttpResponse:
    adt, blob = get_clients()
    try:
        # Prefer JSON body if provided
        body = req.get_body()
        if body:
            try:
                payload = json.loads(body.decode())
                # Expect payload to be a list of prediction entries
                if isinstance(payload, dict):
                    payload = [payload]
                for r in payload:
                    segment_id = r.get("segmentId") or r.get("twinId")
                    if not segment_id:
                        continue
                    patch = []
                    if "predictedAvgSpeed" in r:
                        try:
                            patch.append({"op":"add","path":"/predictedAvgSpeed","value":float(r["predictedAvgSpeed"])})
                        except: pass
                    if "predictedCongestionIndex" in r:
                        try:
                            patch.append({"op":"add","path":"/predictedCongestionIndex","value":float(r["predictedCongestionIndex"])})
                        except: pass
                    if "predictionTimestamp" in r:
                        patch.append({"op":"add","path":"/predictionTimestamp","value":str(r["predictionTimestamp"])})
                    if "predictionHorizon" in r:
                        patch.append({"op":"add","path":"/predictionHorizon","value":str(r["predictionHorizon"])})
                    if patch:
                        adt.update_digital_twin(segment_id, patch)
                return func.HttpResponse("Predictions written (JSON)", status_code=200)
            except Exception:
                pass
        # Fallback to CSV in blob storage
        container = os.environ.get("PREDICTION_CONTAINER", "raw")
        name = os.environ.get("PREDICTION_BLOB", "predictions.csv")
        b = blob.get_blob_client(container, name).download_blob().readall()
        df = pd.read_csv(io.BytesIO(b))
        for _, r in df.iterrows():
            segment_id = r.get("segmentId") or r.get("twinId")
            if not segment_id:
                continue
            patch = []
            if "predictedAvgSpeed" in r:
                try:
                    patch.append({"op":"add","path":"/predictedAvgSpeed","value":float(r["predictedAvgSpeed"])})
                except: pass
            if "predictedCongestionIndex" in r:
                try:
                    patch.append({"op":"add","path":"/predictedCongestionIndex","value":float(r["predictedCongestionIndex"])})
                except: pass
            if "predictionTimestamp" in r:
                patch.append({"op":"add","path":"/predictionTimestamp","value":str(r["predictionTimestamp"])})
            if "predictionHorizon" in r:
                patch.append({"op":"add","path":"/predictionHorizon","value":str(r["predictionHorizon"])})
            if patch:
                adt.update_digital_twin(segment_id, patch)
        return func.HttpResponse("Predictions written (CSV)", status_code=200)
    except Exception as e:
        logging.error(f"Prediction write failed: {e}")
        return func.HttpResponse("Error", status_code=500)
