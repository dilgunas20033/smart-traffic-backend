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
- `fetch_ritis_incidents` (Timer every 10 min): Authenticated HTML RSS incident parsing, lane impact extraction, patches incident properties to v2 twins.

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
| `RITIS_RSS_URL` | RITIS/Regional incident HTML RSS feed URL. |
| `RITIS_LOGIN_URL` | Login form URL for authenticated RITIS session. |
| `RITIS_EMAIL` | Account email for RITIS feed access. |
| `RITIS_PASSWORD` | Account password (consider Key Vault in production). |
| `ROADSEGMENT_V2_ID` | New model ID for RoadSegment v2 (default dtmi:fgcu:traffic:RoadSegment;2). |
| `ROADSEGMENT_V2_SUFFIX` | Suffix for migrated twin IDs (default `_v2`). |
| `ROADSEGMENT_V2_DRY_RUN` | Set `false` to perform migration, otherwise dry run. |

## Segment Mapping
Populate `ingestion/segment_map.csv` with pairs:
```
external_segment_id,adt_segment_id
12345,Segment_001
67890,Segment_002
```
External IDs come from FDOT data; ADT IDs match twins you seeded.

## Data Source (RITIS-Only Mode)
This deployment uses the RITIS incident RSS feed as the sole real-time data source. RITIS aggregates FDOT and regional traffic data. In the absence of a direct per-segment speed feed, we derive a simple congestion heuristic from lane closure ratios:

Congestion Index = AffectedLanes / TotalLanes (clamped 0..1).

The same value is temporarily mirrored to `predictedCongestionIndex` until a predictive model is implemented. When you add a true speed/volume data feed later, remove or override this heuristic.

Deactivate the legacy `fetch_dot_traffic` function by deleting its folder or removing its timer trigger if not used.

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
- HTTP Resilience: Simple retry on 429 for FDOT fetch; extend with exponential/backoff later.
- Auth Resilience: RITIS login heuristics attempt multiple common form field names; failure falls back to direct fetch.
- Idempotency: ADT patch operations are additive and safe to repeat; consider ETag conditions for concurrency.
- Mapping Validation: Unknown external IDs skipped to prevent orphan twins.
- Error Handling: Non-fatal ingestion errors logged; snapshots still attempted.
- Future Hardening: Structured logging (App Insights), schema validation, retry budget, circuit breaker.

## Migration to RoadSegment v2
`dtdl/RoadSegment.v2.json` adds incident properties (lane impact, direction, last update). Existing twins using `;1` cannot change model ID directly; create new twins with a suffix and migrate relationships.

Script: `scripts/migrate_to_v2.py`
1. Set `ADT_ENDPOINT` and optional `ROADSEGMENT_V2_*` vars.
2. Run `python scripts/migrate_to_v2.py` (dry run default).
3. Set `ROADSEGMENT_V2_DRY_RUN=false` to perform migration.
4. Recreate relationships for new twins (connectedTo, hasSensor, hasPavementAsset).
5. Update dashboards / queries to reference suffixed IDs.

Use Azure Key Vault for secrets (RITIS credentials, API keys) in production. `.env.example` included for local convenience.

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
