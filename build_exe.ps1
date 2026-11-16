$ErrorActionPreference = "Stop"

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz

& ".\venv\Scripts\pyinstaller.exe" --noconfirm --clean ".\DownloaderCAD.spec"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$destino = ".\dist\DownloaderCAD"
Copy-Item ".\config.example.json" "$destino\config.example.json" -Force
Copy-Item ".\README.md" "$destino\README.md" -Force
Copy-Item ".\LICENSE" "$destino\LICENSE" -Force
Copy-Item ".\docs\GUIA_USUARIO.md" "$destino\GUIA_USUARIO.md" -Force
if (Test-Path ".\modelo\modelo_planilha.xlsx") {
    Copy-Item ".\modelo\modelo_planilha.xlsx" "$destino\modelo_planilha.xlsx" -Force
}

$zip = ".\dist\DownloaderCAD-portable.zip"
if (Test-Path $zip) {
    Remove-Item $zip -Force
}

# Antivírus/indexador pode segurar um arquivo por alguns segundos logo após o
# build ("o arquivo está sendo usado por outro processo"), então tenta de novo
# antes de desistir.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$tentativas = 3
for ($i = 1; $i -le $tentativas; $i++) {
    try {
        [System.IO.Compression.ZipFile]::CreateFromDirectory(
            (Resolve-Path $destino).Path,
            (Join-Path (Resolve-Path ".\dist").Path "DownloaderCAD-portable.zip"),
            [System.IO.Compression.CompressionLevel]::Optimal,
            $true
        )
        break
    }
    catch {
        if ($i -eq $tentativas) { throw }
        Write-Warning "Compactação falhou ($($_.Exception.Message)). Tentando de novo em 3s..."
        Start-Sleep -Seconds 3
    }
}

$tamanho = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Pronto: $destino\DownloaderCAD.exe"
Write-Host "Pacote: $zip ($tamanho MB)"
