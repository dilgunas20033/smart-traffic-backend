import json
import random
import time
from typing import List, Dict


def generate_predictions(segment_ids: List[str]) -> List[Dict]:
    """
    Generate simple synthetic congestion predictions for given ADT twin IDs.
    Replace this with a real model when ready.
    """
    preds = []
    now = int(time.time())
    for seg_id in segment_ids:
        preds.append(
            {
                "adtSegmentId": seg_id,
                "congestionIndex": round(random.uniform(0.0, 1.0), 3),
                "confidence": round(random.uniform(0.5, 0.99), 3),
                "timestamp": now,
            }
        )
    return preds


if __name__ == "__main__":
    # Example usage: emit JSON to stdout for piping into the HTTP function
    demo_ids = [
        "segment-001",
        "segment-002",
        "segment-003",
    ]
    output = generate_predictions(demo_ids)
    print(json.dumps(output))
