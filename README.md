# DOLINA ELÉTRICA — Dolina dos Maracanãs

Repositório completo dos levantamentos, dados de campo, arquivos geoespaciais e resultados de modelagem de eletrorresistividade da Dolina dos Maracanãs.

## Estrutura

- `01_PROJETO_DOLINA_MARACANAS/`: projeto, documentos e bases geológicas/SIG.
- `02_DADOS_GEOFISICOS/`: dados geofísicos originais e filtrados, topografia e coordenadas.
- `03_FOTOS_DE_CAMPO/`: registro fotográfico das campanhas.
- `04_RECURSOS_FIGURAS_R/`: recursos auxiliares para figuras e análise.
- `05_RESULTADOS_RESIPY/`: inversões 2D, projetos `.resipy`, malhas, CSV, VTK, figuras e relatórios.

## Modelagem ResIPy

Foram produzidas duas inversões conjuntas por linha física:

- Linha 1: DD + WS, 1.478 medições, RMS final 1,10.
- Linha 2: DD + WS + PD, 3.062 medições, RMS final 1,04.

A topografia foi aplicada aos 66 eletrodos de cada linha. A origem de cada leitura permanece identificada nos arquivos `dados_combinados_qc.csv`.

Consulte `05_RESULTADOS_RESIPY/RELATORIO_PROCESSAMENTO.md` para a metodologia, filtros, parâmetros e validação dos resultados.
