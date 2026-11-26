param([switch]$Configure)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$toolsDirectory = Join-Path $projectRoot '.jetfood-tools'
$ngrokDirectory = Join-Path $toolsDirectory 'ngrok'
$ngrokExecutable = Join-Path $ngrokDirectory 'ngrok.exe'
$ngrokConfig = Join-Path $toolsDirectory 'ngrok.yml'

if (-not (Test-Path -LiteralPath $ngrokExecutable)) {
    New-Item -ItemType Directory -Force -Path $toolsDirectory | Out-Null
    $archivePath = Join-Path $toolsDirectory 'ngrok.zip'
    Invoke-WebRequest -Uri 'https://bin.ngrok.com/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile $archivePath -TimeoutSec 60
    Expand-Archive -LiteralPath $archivePath -DestinationPath $ngrokDirectory -Force
}

$signature = Get-AuthenticodeSignature -LiteralPath $ngrokExecutable
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'ngrok, Inc\.') {
    throw 'The official ngrok digital signature could not be verified. The executable was not started.'
}

if ($Configure -or -not (Test-Path -LiteralPath $ngrokConfig)) {
    Write-Host 'Get your ngrok authtoken from https://dashboard.ngrok.com/get-started/your-authtoken'
    Write-Host 'Enter the ngrok token locally. Do not enter the Freedom Pay payment secret here.'
    $secureToken = Read-Host 'ngrok authtoken (hidden)' -AsSecureString
    $tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    try {
        $plainToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
        if ([string]::IsNullOrWhiteSpace($plainToken)) { throw 'No ngrok authtoken was supplied.' }
        $configurationOutput = & $ngrokExecutable config add-authtoken $plainToken --config $ngrokConfig 2>&1
        if ($LASTEXITCODE -ne 0) { throw 'ngrok account configuration failed. Check your token locally.' }
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
        $plainToken = $null
        $configurationOutput = $null
        $secureToken.Dispose()
    }
}

Write-Host 'Starting a public tunnel to local Django on port 8000. Keep this terminal open.'
Write-Host 'Use only for local sandbox testing. Stop with Ctrl+C when finished.'
Write-Host 'Copy the displayed HTTPS origin into: py manage.py setup_test_payments'
& $ngrokExecutable http http://127.0.0.1:8000 --config $ngrokConfig
exit $LASTEXITCODE
