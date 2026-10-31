# Execução interrompida por solicitação do usuário

A execução foi encerrada em 30/10/2026 durante a inversão real `L1-WS` e não
deve ser retomada automaticamente.

## Estado dos artefatos incluídos

- `L1_DD`: fluxo completo (inversão real, forward sintético, reinversão
  sintética, métricas e comparação gráfica).
- `L1_WS`: apenas imagens preliminares já produzidas antes da interrupção
  (`01_pseudosecao_observada.png` e `02_malha_quadrilateral.png`). Não existe
  resultado de inversão válido para este caso nesta pasta.
- `L2_DD`, `L2_WS` e `L2_PD`: não iniciados.

Os notebooks em `06_SCRIPTS_PROCESSAMENTO/notebooks/` usam uma pasta de saída
nova e não retomam esta execução parcial.
