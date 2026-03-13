[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$CreateRepositoryIfMissing,
    [switch]$NoAllowUnauthenticated
)

$ErrorActionPreference = 'Stop'

function Get-RequiredEnv([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required environment variable '$Name' is not set."
    }
    return $value.Trim()
}

function Get-OptionalEnv([string]$Name, [string]$Default = '') {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }
    return $value.Trim()
}

function Invoke-Gcloud([string[]]$Args) {
    Write-Host ("gcloud " + ($Args -join ' '))
    & gcloud @Args
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed with exit code $LASTEXITCODE"
    }
}

$projectId = Get-RequiredEnv 'GOOGLE_CLOUD_PROJECT'
$region = Get-OptionalEnv 'GOOGLE_CLOUD_LOCATION' 'us-central1'
$serviceName = Get-OptionalEnv 'CLOUD_RUN_SERVICE' 'ghostline-backend'
$repository = Get-OptionalEnv 'ARTIFACT_REGISTRY_REPOSITORY' 'ghostline-images'
$imageName = Get-OptionalEnv 'ARTIFACT_IMAGE_NAME' 'ghostline-backend'
$appName = Get-OptionalEnv 'APP_NAME' 'ghostline'
$appEnv = Get-OptionalEnv 'APP_ENV' 'production'
$logLevel = Get-OptionalEnv 'LOG_LEVEL' 'INFO'
$vertexModel = Get-OptionalEnv 'VERTEX_AI_MODEL' 'gemini-live-2.5-flash-native-audio'
$inputTranscription = Get-OptionalEnv 'GEMINI_LIVE_INPUT_TRANSCRIPTION' 'true'
$outputTranscription = Get-OptionalEnv 'GEMINI_LIVE_OUTPUT_TRANSCRIPTION' 'true'
$mockVerification = Get-OptionalEnv 'MOCK_VERIFICATION_ENABLED' 'false'
$demoModeDefault = Get-OptionalEnv 'DEMO_MODE_DEFAULT' 'false'
$firestoreDatabase = Get-OptionalEnv 'FIRESTORE_DATABASE' '(default)'
$firestoreCollection = Get-OptionalEnv 'FIRESTORE_SESSIONS_COLLECTION' 'ghostline_sessions'
$serviceAccount = Get-OptionalEnv 'CLOUD_RUN_SERVICE_ACCOUNT' ''
$timeoutSeconds = Get-OptionalEnv 'CLOUD_RUN_TIMEOUT_SECONDS' '3600'
$allowUnauthenticated = -not $NoAllowUnauthenticated.IsPresent
$imageUri = "$region-docker.pkg.dev/$projectId/$repository/$imageName"

$repoRoot = Split-Path -Parent $PSScriptRoot
$serverDir = Join-Path $repoRoot 'server'

Write-Host "Project: $projectId"
Write-Host "Region: $region"
Write-Host "Service: $serviceName"
Write-Host "Image: $imageUri"
Write-Host "Server dir: $serverDir"

Invoke-Gcloud @('config', 'set', 'project', $projectId)

if ($CreateRepositoryIfMissing.IsPresent) {
    Invoke-Gcloud @(
        'artifacts', 'repositories', 'create', $repository,
        '--repository-format=docker',
        '--location', $region
    )
}

if (-not $SkipBuild.IsPresent) {
    Invoke-Gcloud @('builds', 'submit', $serverDir, '--tag', $imageUri)
}

$envVars = @(
    "APP_NAME=$appName",
    "APP_ENV=$appEnv",
    "LOG_LEVEL=$logLevel",
    "GOOGLE_CLOUD_PROJECT=$projectId",
    "GOOGLE_CLOUD_LOCATION=$region",
    "VERTEX_AI_MODEL=$vertexModel",
    "GEMINI_LIVE_INPUT_TRANSCRIPTION=$inputTranscription",
    "GEMINI_LIVE_OUTPUT_TRANSCRIPTION=$outputTranscription",
    "MOCK_VERIFICATION_ENABLED=$mockVerification",
    "DEMO_MODE_DEFAULT=$demoModeDefault",
    "FIRESTORE_DATABASE=$firestoreDatabase",
    "FIRESTORE_SESSIONS_COLLECTION=$firestoreCollection",
    "CLOUD_RUN_SERVICE=$serviceName"
)

$deployArgs = @(
    'run', 'deploy', $serviceName,
    '--image', $imageUri,
    '--region', $region,
    '--platform', 'managed',
    '--port', '8080',
    '--timeout', $timeoutSeconds,
    '--set-env-vars', ($envVars -join ',')
)

if ($allowUnauthenticated) {
    $deployArgs += '--allow-unauthenticated'
}

if (-not [string]::IsNullOrWhiteSpace($serviceAccount)) {
    $deployArgs += @('--service-account', $serviceAccount)
}

Invoke-Gcloud $deployArgs

Write-Host ''
Write-Host 'Deployment complete.'
Write-Host "Service URL:"
Invoke-Gcloud @('run', 'services', 'describe', $serviceName, '--region', $region, '--format=value(status.url)')
