param(
    [string]$Server = "138.197.65.67",
    [string]$User = "root",
    [string]$RemoteDir = "/opt/control-accesos",
    [string]$ProjectDir = "",
    [string]$KeyPath = "",
    [switch]$UseDefaults,
    [switch]$SkipExtract,
    [switch]$ExtractOnly,
    [switch]$KeepArchive,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host "Uso:"
    Write-Host "  .\subir_droplet.ps1"
    Write-Host "  .\subir_droplet.ps1 -UseDefaults"
    Write-Host "  .\subir_droplet.ps1 -Server 138.197.65.67 -User root -RemoteDir /opt/control-accesos"
    Write-Host ""
    Write-Host "Opciones utiles:"
    Write-Host "  -UseDefaults   No pregunta valores; usa los parametros/defaults."
    Write-Host "  -SkipExtract   Solo sube el paquete a /tmp; no extrae en el servidor."
    Write-Host "  -ExtractOnly   Solo extrae /tmp/control-accesos-deploy.tar.gz en el servidor."
    Write-Host "  -KeepArchive   Conserva el .tar.gz local al terminar."
}

function Read-Default {
    param(
        [string]$Label,
        [string]$Default
    )

    $value = Read-Host "$Label [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }

    return $value.Trim()
}

function Test-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No encontre '$Name' en PATH."
    }
}

function Invoke-Native {
    param(
        [string]$Description,
        [string]$Exe,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Description"
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description fallo con codigo $LASTEXITCODE."
    }
}

function Quote-Sh {
    param([string]$Value)

    return "'" + ($Value -replace "'", "'\''") + "'"
}

if ($Help) {
    Show-Help
    exit 0
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectDir)) {
    $ProjectDir = Join-Path $ScriptDir "access-manager"
}
if ([string]::IsNullOrWhiteSpace($KeyPath)) {
    $KeyPath = Join-Path $ScriptDir "access-manager\control_accesos_staging"
}

if (-not $UseDefaults) {
    Write-Host ""
    Write-Host "Subida interactiva al droplet"
    Write-Host "Puedes presionar Enter para aceptar cada valor."
    Write-Host ""
    $Server = Read-Default "IP o dominio del droplet" $Server
    $User = Read-Default "Usuario SSH" $User
    $RemoteDir = Read-Default "Carpeta destino remota" $RemoteDir
    $ProjectDir = Read-Default "Carpeta local del proyecto" $ProjectDir
    $KeyPath = Read-Default "Llave privada SSH" $KeyPath
}

$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$KeyPath = [System.IO.Path]::GetFullPath($KeyPath)
$Remote = "$User@$Server"
$RemoteArchive = "/tmp/control-accesos-deploy.tar.gz"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LocalArchive = Join-Path ([System.IO.Path]::GetTempPath()) "control-accesos-deploy-$Timestamp.tar.gz"
$createdArchive = $false

try {
    Test-Command "ssh"
    Test-Command "scp"
    Test-Command "tar"

    if (-not (Test-Path -LiteralPath $ProjectDir -PathType Container)) {
        throw "No existe la carpeta local del proyecto: $ProjectDir"
    }
    if (-not (Test-Path -LiteralPath $KeyPath -PathType Leaf)) {
        throw "No existe la llave privada SSH: $KeyPath"
    }
    if ($SkipExtract -and $ExtractOnly) {
        throw "No puedes usar -SkipExtract y -ExtractOnly al mismo tiempo."
    }

    Write-Host ""
    Write-Host "Resumen:"
    Write-Host "  Local:   $ProjectDir"
    Write-Host "  Remoto:  ${Remote}:$RemoteDir"
    Write-Host "  Llave:   $KeyPath"
    Write-Host ""
    Write-Host "Nota: si la llave tiene passphrase, SSH la pedira durante scp y ssh."

    if (-not $ExtractOnly) {
        $keyName = Split-Path -Leaf $KeyPath
        $excludePatterns = @(
            ".git",
            ".env",
            ".env.local",
            ".env.production",
            ".env.staging",
            "node_modules",
            "dist",
            "build",
            "__pycache__",
            ".pytest_cache",
            ".venv",
            ".ssh",
            "id_rsa",
            "id_rsa.pub",
            "id_ed25519",
            "id_ed25519.pub",
            "*.pem",
            "*.key",
            $keyName,
            "$keyName.pub"
        ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

        $tarArgs = @("-czf", $LocalArchive)
        foreach ($pattern in $excludePatterns) {
            $tarArgs += @("--exclude", $pattern)
        }
        $tarArgs += @("-C", $ProjectDir, ".")

        Invoke-Native "Empaquetando codigo local" "tar" $tarArgs
        $createdArchive = $true

        Invoke-Native "Subiendo paquete a ${Remote}:$RemoteArchive" "scp" @(
            "-i", $KeyPath,
            "-o", "StrictHostKeyChecking=accept-new",
            $LocalArchive,
            "${Remote}:$RemoteArchive"
        )
    }
    else {
        Write-Host ""
        Write-Host "Modo ExtractOnly: usare el paquete remoto existente en $RemoteArchive."
    }

    if (-not $SkipExtract) {
        $remoteDirQ = Quote-Sh $RemoteDir
        $remoteArchiveQ = Quote-Sh $RemoteArchive
        $remoteCommand = "set -e; mkdir -p $remoteDirQ; tar -xzf $remoteArchiveQ -C $remoteDirQ; rm -f $remoteArchiveQ; printf 'Archivos en destino: '; find $remoteDirQ -mindepth 1 -maxdepth 1 | wc -l"

        Invoke-Native "Extrayendo paquete en $RemoteDir" "ssh" @(
            "-i", $KeyPath,
            "-o", "StrictHostKeyChecking=accept-new",
            $Remote,
            $remoteCommand
        )
    }
    else {
        Write-Host ""
        Write-Host "SkipExtract activo: el paquete quedo en ${Remote}:$RemoteArchive"
    }

    Write-Host ""
    Write-Host "Subida completada correctamente."
}
catch {
    Write-Host ""
    Write-Host "Fallo la subida: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    if ($createdArchive -and -not $KeepArchive -and (Test-Path -LiteralPath $LocalArchive)) {
        Remove-Item -LiteralPath $LocalArchive -Force
    }
    elseif ($createdArchive -and $KeepArchive) {
        Write-Host "Paquete local conservado: $LocalArchive"
    }
}
