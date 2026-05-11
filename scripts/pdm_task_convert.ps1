param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,

    [string]$OutputPath = "",

    [string]$ApiUrl = "http://127.0.0.1:8787/api/v1/convert",
    [string]$TemplatePath = "",
    [double]$PrecioDefaultKg = 0.0,
    [string]$FabricanteDefault = "INNOVAX"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "llm_globalshop_api_client.py"
if (-not (Test-Path $scriptPath)) {
    Write-Error "No existe cliente API: $scriptPath"
    exit 11
}

$args = @(
    $scriptPath,
    "--source", $SourcePath,
    "--api-url", $ApiUrl,
    "--precio-default-kg", "$PrecioDefaultKg",
    "--fabricante-default", $FabricanteDefault
)

if ($OutputPath -and $OutputPath.Trim().Length -gt 0) {
    $args += @("--output", $OutputPath)
}

if ($TemplatePath -and $TemplatePath.Trim().Length -gt 0) {
    $args += @("--template", $TemplatePath)
}

& py @args
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Error "Fallo conversion LLM (exit code $exitCode)"
    exit $exitCode
}

Write-Host "Conversion LLM completada correctamente."
exit 0
