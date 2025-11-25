import os, json, sys
from azure.identity import DefaultAzureCredential
from azure.digitaltwins.core import DigitalTwinsClient

"""Export ADT twin IDs (optionally filtering by model) to help build segment_map.csv.
Usage:
  python tools/export_twin_ids.py > twins.txt
  python tools/export_twin_ids.py dtmi:fgcu:traffic:RoadSegment;2 > segments.csv
If a model ID is provided, outputs CSV: external_segment_id,adt_segment_id (with blank external id placeholders).
"""

def main():
    endpoint = os.environ.get("ADT_ENDPOINT")
    if not endpoint:
        print("ADT_ENDPOINT not set", file=sys.stderr)
        sys.exit(1)
    cred = DefaultAzureCredential()
    client = DigitalTwinsClient(endpoint, cred)
    model_filter = sys.argv[1] if len(sys.argv) > 1 else None
    query = "SELECT * FROM digitaltwins"
    twins = client.query_twins(query)
    if model_filter:
        print("external_segment_id,adt_segment_id")
    count = 0
    for twin in twins:
        twin_id = twin.get('$dtId') or twin.get('id')
        model_id = twin.get('$metadata', {}).get('$model') or twin.get('$model')
        if model_filter and model_id != model_filter:
            continue
        if model_filter:
            print(f",{twin_id}")  # leave external segment id blank to fill manually
        else:
            print(twin_id)
        count += 1
    print(f"Exported {count} twin IDs", file=sys.stderr)

if __name__ == '__main__':
    main()
