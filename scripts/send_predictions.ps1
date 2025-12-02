param(
    [string]$Url = "http://localhost:7071/api/write_predictions",
    [string]$JsonFile = "ml\sample_predictions.json"
)

if (-not (Test-Path $JsonFile)) {
    Write-Error "JSON file not found: $JsonFile"
    exit 1
}

$body = Get-Content -Path $JsonFile -Raw
Write-Host "Sending predictions to $Url"

$response = Invoke-RestMethod -Method Post -Uri $Url -Body $body -ContentType "application/json"
Write-Output $response
