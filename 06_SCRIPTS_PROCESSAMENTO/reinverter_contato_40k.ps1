param(
    [string]$RaizDados = 'C:\Users\RT09B\Desktop\WILLIAM\WILLIAM\DOLINA-20261030T170722Z-1-001\DOLINA DOS MARACANAS',
    [string]$Saida = '',
    [double]$LimiteOhm = 40000
)

$ErrorActionPreference = 'Stop'
$WorkDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceDir = Split-Path -Parent $WorkDir
$ProcessScript = Join-Path $WorkDir 'process_dolina_resipy.py'
$LocalPython = Join-Path $WorkDir 'resipy-env\Scripts\python.exe'
$WorkspacePython = Join-Path $WorkspaceDir 'work\resipy-env\Scripts\python.exe'

if (Test-Path -LiteralPath $LocalPython -PathType Leaf) {
    $PythonExe = $LocalPython
} elseif (Test-Path -LiteralPath $WorkspacePython -PathType Leaf) {
    $PythonExe = $WorkspacePython
} else {
    $PythonExe = (Get-Command python.exe -ErrorAction Stop).Source
}

if ([string]::IsNullOrWhiteSpace($Saida)) {
    $Saida = Join-Path $WorkspaceDir 'outputs\ResIPy_Dolina_Maracanas_CONTATO_MAX_40k'
}

if (-not (Test-Path -LiteralPath $RaizDados -PathType Container)) {
    throw "Raiz de dados não encontrada: $RaizDados"
}
if (Test-Path -LiteralPath $Saida) {
    throw "A pasta de saída já existe. Informe outra com -Saida para preservar resultados: $Saida"
}

& $PythonExe $ProcessScript $RaizDados $Saida --contact-max-ohm $LimiteOhm
if ($LASTEXITCODE -ne 0) {
    throw "A reinversão terminou com código $LASTEXITCODE. Consulte resumos.json na saída."
}

Write-Host "Reinversão concluída em: $Saida"
