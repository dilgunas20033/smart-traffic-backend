Param(
    [Parameter(Mandatory=$true)][string]$ConnectionString,
    [string]$SegmentMapPath = "ingestion/seed_segments.json", # path to segment map source (CSV or JSON)
    [string]$SegmentMapBlob = "segment_map.csv",
    [string]$SegmentMapContainer = "raw",
    [string]$SeedContainer = "seed"
)

# Fail fast if az not installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI 'az' is required. Install from https://learn.microsoft.com/cli/azure/install-azure-cli-windows";
    exit 1
}

$settingsFile = "functions/adt_ingest/local.settings.json"
if (-not (Test-Path $settingsFile)) {
    Write-Error "Could not find $settingsFile. Run from repo root."; exit 1
}

# Update local.settings.json AzureWebJobsStorage & STORAGE_CONNECTION_STRING
$json = Get-Content $settingsFile | ConvertFrom-Json
$json.Values.AzureWebJobsStorage = $ConnectionString
$json.Values.STORAGE_CONNECTION_STRING = $ConnectionString

# Persist
$json | ConvertTo-Json -Depth 5 | Out-File $settingsFile -Encoding UTF8
Write-Host "Updated AzureWebJobsStorage and STORAGE_CONNECTION_STRING in $settingsFile" -ForegroundColor Green

# Create containers
az storage container create --name $SegmentMapContainer --connection-string $ConnectionString --output none
az storage container create --name $SeedContainer --connection-string $ConnectionString --output none
Write-Host "Ensured containers '$SegmentMapContainer' and '$SeedContainer' exist." -ForegroundColor Green

# Upload segment map if CSV present
if (Test-Path $SegmentMapPath) {
    az storage blob upload --file $SegmentMapPath --connection-string $ConnectionString --container-name $SegmentMapContainer --name $SegmentMapBlob --overwrite --output none
    Write-Host "Uploaded segment map blob: $SegmentMapBlob" -ForegroundColor Green
} else {
    Write-Warning "Segment map source file not found at $SegmentMapPath. Skipping upload."
}

Write-Host "Local setup complete. Start Functions host with: cd functions/adt_ingest; func start --verbose" -ForegroundColor Cyan
