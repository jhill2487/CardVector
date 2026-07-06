param(
  [Parameter(Mandatory=$true)]
  [string]$ExtensionId
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$templatePath = Join-Path $root "native-host-manifest.template.json"
$manifestPath = Join-Path $root "com.putnam.pokemon_watcher.json"
$hostBatPath = Join-Path $root "run_native_host.bat"

$manifest = Get-Content -LiteralPath $templatePath -Raw
$manifest = $manifest.Replace("__EXTENSION_ID__", $ExtensionId)
$manifest = $manifest.Replace("__HOST_BAT_PATH__", ($hostBatPath.Replace("\", "\\")))
Set-Content -LiteralPath $manifestPath -Value $manifest -Encoding UTF8

$registryPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.putnam.pokemon_watcher"
New-Item -Path $registryPath -Force | Out-Null
Set-Item -Path $registryPath -Value $manifestPath

Write-Host "Installed native messaging host:"
Write-Host $manifestPath
