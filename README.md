# Smart Traffic Backend (FGCU)

Cloud backend integrating Florida Department of Transportation (FDOT) traffic & pavement data into Azure Digital Twins (ADT) with prediction fields and query APIs.

## What This Does
- Defines digital models for Roads, Segments, Sensors, Pavement Assets.
- Fetches real-time (or near real-time) Florida traffic data on a schedule and patches current speed/volume into ADT twins.
- Stores raw snapshots for future historical & ML use.
- Exposes HTTP endpoints to query segments and congestion.
- Supports writing prediction values back into twins (future: automated ML pipeline).

## Folder Overview
```
dtdl/                  DTDL model JSON definitions
functions/adt_ingest/  Azure Functions (HTTP + Timer triggers)
ingestion/             CSV seeds, segment mapping, history snapshots
```

## New Functions Added
- `fetch_dot_traffic` (Timer every 5 min): Pulls FDOT data, normalizes, updates twins, stores snapshot.
- `list_segments` (HTTP GET /segments): Returns all segment twins and key fields.

## Environment Variables (local.settings.json or Azure App Settings)
| Name | Purpose |
|------|---------|
| `ADT_ENDPOINT` | Base URL of your ADT instance (e.g. https://<name>.api.<region>.digitaltwins.azure.net) |
| `STORAGE_ACCOUNT_NAME` | Storage account name for blob snapshots & mapping file. |
| `FDOT_TRAFFIC_API_URL` | Florida traffic data endpoint (see below). |
| `FDOT_API_KEY` | API key or token if FDOT endpoint requires auth (optional). |
| `SEGMENT_MAP_CONTAINER` | Blob container holding `segment_map.csv` (default `raw`). |
| `SEGMENT_MAP_BLOB` | Blob name (default `segment_map.csv`). |
| `TRAFFIC_HISTORY_CONTAINER` | Container for snapshot archives (default `raw`). |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | (Optional) Enable richer telemetry. |

## Segment Mapping
Populate `ingestion/segment_map.csv` with pairs:
```
external_segment_id,adt_segment_id
12345,Segment_001
67890,Segment_002
```
External IDs come from FDOT data; ADT IDs match twins you seeded.

## FDOT Data Source Options
You can obtain Florida traffic data from:
1. Florida Open Data Portal (search for "Traffic", "Speed", "Volume"): https://data.fdot.gov/
2. Statewide FDOT ITS data (detector feeds) often accessible through regional XML/JSON endpoints.
3. National Transportation Data (USDOT / Bureau of Transportation Statistics): https://data.transportation.gov/ (filter for Florida & roadway performance).

If you need a key or registration, create an account at:
- Florida Open Data Portal: https://data.fdot.gov/ (Sign In / Register top right)
- USDOT Open Data (for supplemental datasets): https://data.transportation.gov/signup

Pick a dataset offering per-segment speed & volume. Get the API endpoint (usually a Socrata-style URL ending with `.json` or including `?$query=`). Set that as `FDOT_TRAFFIC_API_URL`.

### Example Socrata API Pattern
```
https://data.fdot.gov/resource/<dataset_id>.json?$limit=5000
```
Add filters for date/time if required. If the portal uses App Tokens, add it to `FDOT_API_KEY` (Bearer or header token depending on docs).

## Running Locally
Install requirements inside the Functions folder (from repo root in PowerShell):
```powershell
cd "functions/adt_ingest"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
func start
```
Timer function will start executing (every 5 min). To test HTTP endpoints:
```powershell
curl http://localhost:7071/api/segments
curl http://localhost:7071/api/get_congestion_top?threshold=0.7
```

## Adding More Endpoints
Future additions: pavement status listing, historical export, sensor health, prediction pipeline trigger.

## Resilience Notes
- Retries: Basic backoff on HTTP 429 (rate limit). Enhance with exponential strategy later.
- Idempotency: ADT patch operations safe to repeat.
- Logging: Azure Functions logs show update counts.

## Next Steps
1. Acquire actual FDOT endpoint + token; set env vars.
2. Complete `segment_map.csv` using real segment IDs.
3. Seed ADT with segments matching mapping.
4. Verify timer function updates speed/volume fields.
5. Add pavement ingestion (daily) if dataset available.
6. Implement historical ML training pipeline.

## Cost Considerations (To Document Later)
- Function executions (every 5 min) vs data size
- Storage snapshot frequency
- ADT query load from dashboard
- ML training cadence

## License / Usage
Internal academic project (FGCU) using public transportation data. Respect FDOT terms of use when calling APIs.
