param(
    [Parameter(Mandatory = $true)]
    [string]$Target
)

$ErrorActionPreference = 'Stop'
$expectedTarget = 'C:\Users\RT09B\Desktop\WILLIAM\WILLIAM\DOLINA-20261030T170722Z-1-001\DOLINA'
$targetPath = (Resolve-Path -LiteralPath $Target).Path.TrimEnd('\')

if (-not [StringComparer]::OrdinalIgnoreCase.Equals($targetPath, $expectedTarget)) {
    throw "Destino inesperado. Esperado: $expectedTarget | Recebido: $targetPath"
}

if (-not (Test-Path -LiteralPath (Join-Path $targetPath 'DOLINA') -PathType Container)) {
    throw 'A pasta interna DOLINA não foi encontrada. A estrutura pode já ter sido organizada.'
}

foreach ($marker in @('00_COMECE_AQUI', '01_PROJETO_DOLINA_MARACANAS', '99_DUPLICADOS_CONFIRMADOS')) {
    if (Test-Path -LiteralPath (Join-Path $targetPath $marker)) {
        throw "Marcador de organização já existe: $marker. Operação cancelada para evitar sobreposição."
    }
}

$beforeFiles = @(Get-ChildItem -LiteralPath $targetPath -File -Recurse -Force)
$beforeCount = $beforeFiles.Count
$beforeBytes = ($beforeFiles | Measure-Object -Property Length -Sum).Sum
$moves = [System.Collections.Generic.List[object]]::new()

function Assert-InTarget {
    param([string]$Path)
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $prefix = $targetPath + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -and
        -not [StringComparer]::OrdinalIgnoreCase.Equals($full, $targetPath)) {
        throw "Caminho fora do destino autorizado: $full"
    }
    return $full
}

function Ensure-Directory {
    param([string]$RelativePath)
    $full = Assert-InTarget (Join-Path $targetPath $RelativePath)
    if (-not (Test-Path -LiteralPath $full -PathType Container)) {
        New-Item -ItemType Directory -Path $full | Out-Null
    }
    return $full
}

function Move-Safely {
    param(
        [string]$SourceRelative,
        [string]$DestinationRelative,
        [string]$Reason
    )
    $source = Assert-InTarget (Join-Path $targetPath $SourceRelative)
    $destination = Assert-InTarget (Join-Path $targetPath $DestinationRelative)
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Origem ausente: $SourceRelative"
    }
    if (Test-Path -LiteralPath $destination) {
        throw "Destino já existe: $DestinationRelative"
    }
    $destinationParent = Split-Path -Parent $destination
    Assert-InTarget $destinationParent | Out-Null
    if (-not (Test-Path -LiteralPath $destinationParent -PathType Container)) {
        New-Item -ItemType Directory -Path $destinationParent | Out-Null
    }
    Move-Item -LiteralPath $source -Destination $destination
    $moves.Add([PSCustomObject]@{
        Origem = $SourceRelative
        Destino = $DestinationRelative
        Motivo = $Reason
        DataHora = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    })
}

Ensure-Directory '00_COMECE_AQUI' | Out-Null
Ensure-Directory '90_VARIANTES_PARA_REVISAO' | Out-Null
Ensure-Directory '99_DUPLICADOS_CONFIRMADOS' | Out-Null

# Árvores completas que repetem conteúdo já existente ou representam backups paralelos.
Move-Safely 'FOTOS' '99_DUPLICADOS_CONFIRMADOS\FOTOS_EXTERNA_COPIA_INTEGRAL' 'Cópia integral confirmada por caminho relativo e SHA-256 (80 de 80 arquivos).'
Move-Safely 'DOLINA\Geologia_SHP_Buraco_das_Araras' '99_DUPLICADOS_CONFIRMADOS\GEOLOGIA_SIG_COPIA_INTEGRAL' 'Os 47 arquivos são idênticos aos do projeto integrado; a versão ativa contém ainda o mapa adicional.'
Move-Safely 'Dados_Dolina_Buraco_das_Araras' '90_VARIANTES_PARA_REVISAO\BACKUP_DADOS_GEOFISICOS_EXTERNO' 'Backup paralelo: 15 arquivos idênticos e 5 documentos com versões diferentes; preservado integralmente para revisão.'

# Separa arquivos com sufixo (1): cópias byte a byte vão para duplicados; variantes ficam para revisão.
$canonicalRoots = @(
    'DOLINA\LEIA-ME_PROJETO_DOLINA (1).md.docx',
    'DOLINA\00_PROJETO_DOLINA_MARACANAS',
    'DOLINA\Dados_Dolina_Buraco_das_Araras'
)
$counterFiles = [System.Collections.Generic.List[IO.FileInfo]]::new()
foreach ($relativeRoot in $canonicalRoots) {
    $fullRoot = Join-Path $targetPath $relativeRoot
    if (Test-Path -LiteralPath $fullRoot -PathType Leaf) {
        $counterFiles.Add((Get-Item -LiteralPath $fullRoot))
    } elseif (Test-Path -LiteralPath $fullRoot -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $fullRoot -File -Recurse -Force | Where-Object { $_.Name -match '\(1\)' }) {
            $counterFiles.Add($file)
        }
    }
}

foreach ($file in @($counterFiles | Sort-Object FullName -Unique)) {
    $sourceRelative = $file.FullName.Substring($targetPath.Length + 1)
    $counterpartName = $file.Name -replace '\s*\(1\)', ''
    $counterpart = Join-Path $file.DirectoryName $counterpartName
    $isIdentical = $false
    if (Test-Path -LiteralPath $counterpart -PathType Leaf) {
        $isIdentical = ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -eq
                        (Get-FileHash -LiteralPath $counterpart -Algorithm SHA256).Hash)
    }
    if ($isIdentical) {
        Move-Safely $sourceRelative (Join-Path '99_DUPLICADOS_CONFIRMADOS\ARQUIVOS_COM_SUFIXO_1' $sourceRelative) 'Cópia com sufixo (1) idêntica ao arquivo sem o sufixo, confirmada por SHA-256.'
    } else {
        Move-Safely $sourceRelative (Join-Path '90_VARIANTES_PARA_REVISAO\ARQUIVOS_COM_SUFIXO_1' $sourceRelative) 'Arquivo com sufixo (1) difere do correspondente ou não possui correspondente exato; preservado para decisão humana.'
    }
}

# Consolida a árvore ativa na raiz.
Move-Safely 'DOLINA\LEIA-ME_PROJETO_DOLINA.md.docx' '00_COMECE_AQUI\LEIA-ME_PROJETO_DOLINA.md.docx' 'Documento geral do projeto colocado no ponto de entrada.'
Move-Safely 'DOLINA\00_PROJETO_DOLINA_MARACANAS' '01_PROJETO_DOLINA_MARACANAS' 'Projeto integrado consolidado na raiz.'
Move-Safely 'DOLINA\Dados_Dolina_Buraco_das_Araras' '02_DADOS_GEOFISICOS' 'Dados de campo consolidados em uma única pasta ativa.'
Move-Safely 'DOLINA\FOTOS' '03_FOTOS_DE_CAMPO' 'Coleção canônica de fotos consolidada na raiz.'

# Recursos R não são dados de campo; recebem área própria.
Move-Safely '02_DADOS_GEOFISICOS\skills_R_figuras' '04_RECURSOS_FIGURAS_R' 'Scripts, estilos e instruções R separados dos dados geofísicos.'

# A pasta contém referências/localização de originais, não as fotos propriamente ditas.
Move-Safely '01_PROJETO_DOLINA_MARACANAS\04_DADOS_E_FOTOS_ORIGINAIS' '01_PROJETO_DOLINA_MARACANAS\04_REFERENCIAS_ORIGINAIS' 'Nome corrigido para refletir o conteúdo real da pasta.'

# Fotos organizadas por data presente no nome do arquivo.
$photoRoot = Join-Path $targetPath '03_FOTOS_DE_CAMPO'
foreach ($photo in @(Get-ChildItem -LiteralPath $photoRoot -File -Force)) {
    if ($photo.Name -match '^IMG-(\d{4})(\d{2})(\d{2})-') {
        $dateFolder = "$($Matches[1])-$($Matches[2])-$($Matches[3])"
    } else {
        $dateFolder = 'SEM_DATA_IDENTIFICAVEL'
    }
    $sourceRelative = $photo.FullName.Substring($targetPath.Length + 1)
    $destinationRelative = Join-Path (Join-Path '03_FOTOS_DE_CAMPO' $dateFolder) $photo.Name
    Move-Safely $sourceRelative $destinationRelative 'Foto agrupada pela data codificada no nome.'
}

# A antiga pasta intermediária só é removida se estiver realmente vazia.
$innerFolder = Join-Path $targetPath 'DOLINA'
$remaining = @(Get-ChildItem -LiteralPath $innerFolder -Force)
if ($remaining.Count -ne 0) {
    throw "A pasta intermediária ainda contém $($remaining.Count) item(ns); não será removida."
}
Assert-InTarget $innerFolder | Out-Null
Remove-Item -LiteralPath $innerFolder

# Validação antes de adicionar os documentos administrativos novos.
$afterMoveFiles = @(Get-ChildItem -LiteralPath $targetPath -File -Recurse -Force)
$afterMoveCount = $afterMoveFiles.Count
$afterMoveBytes = ($afterMoveFiles | Measure-Object -Property Length -Sum).Sum
if ($afterMoveCount -ne $beforeCount -or $afterMoveBytes -ne $beforeBytes) {
    throw "Falha de integridade: antes=$beforeCount arquivos/$beforeBytes bytes; depois=$afterMoveCount arquivos/$afterMoveBytes bytes."
}

$manifestPath = Join-Path $targetPath '00_COMECE_AQUI\MANIFESTO_MOVIMENTACOES.csv'
$moves | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding utf8

$topSummary = Get-ChildItem -LiteralPath $targetPath -Directory -Force | Sort-Object Name | ForEach-Object {
    $files = @(Get-ChildItem -LiteralPath $_.FullName -File -Recurse -Force)
    [PSCustomObject]@{
        Pasta = $_.Name
        Arquivos = $files.Count
        TamanhoMB = [math]::Round((($files | Measure-Object -Property Length -Sum).Sum / 1MB), 2)
    }
}
$summaryLines = $topSummary | ForEach-Object { "- $($_.Pasta): $($_.Arquivos) arquivo(s), $($_.TamanhoMB) MB" }

$readme = @"
ORGANIZAÇÃO DA PASTA DOLINA
Data: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

ONDE ENCONTRAR CADA COISA

00_COMECE_AQUI
  Documentação geral e manifesto completo das movimentações.

01_PROJETO_DOLINA_MARACANAS
  Projeto integrado: modelo 3D, geologia/SIG, estratigrafia/interpretação e referências originais.

02_DADOS_GEOFISICOS
  Dados brutos, filtrados, seções e referências das campanhas 20262210 e 20262410.

03_FOTOS_DE_CAMPO
  Fotos organizadas em subpastas por data (AAAA-MM-DD).

04_RECURSOS_FIGURAS_R
  Scripts R, estilos e instruções para geração de figuras.

90_VARIANTES_PARA_REVISAO
  Arquivos com sufixo (1) que diferem do correspondente e o backup externo de dados que contém versões documentais diferentes. Nada foi descartado.

99_DUPLICADOS_CONFIRMADOS
  Cópias integrais ou arquivos com sufixo (1) confirmados como idênticos por SHA-256. Foram isolados para não atrapalhar a navegação; nada foi apagado.

REGRAS IMPORTANTES

- Conjuntos GIS foram mantidos completos: SHP, DBF, SHX, PRJ, CPG e arquivos auxiliares continuam juntos.
- Nenhum dos $beforeCount arquivos originais foi excluído.
- O total original de $([math]::Round($beforeBytes / 1MB, 2)) MB foi preservado.
- Consulte MANIFESTO_MOVIMENTACOES.csv para localizar qualquer item pelo caminho antigo e pelo novo.

RESUMO FINAL

$($summaryLines -join [Environment]::NewLine)
"@
Set-Content -LiteralPath (Join-Path $targetPath '00_COMECE_AQUI\LEIA-ME_ORGANIZACAO.txt') -Value $readme -Encoding utf8

Write-Output "ORGANIZACAO_CONCLUIDA"
Write-Output "ARQUIVOS_ORIGINAIS=$beforeCount"
Write-Output "BYTES_ORIGINAIS=$beforeBytes"
Write-Output "MOVIMENTACOES=$($moves.Count)"
$topSummary | Format-Table -AutoSize
