# Inversões combinadas quadrilaterais e ensaios sintéticos

Execução: 2026-10-31T03:06:54
ResIPy: 3.6.6

- L1: DD + WS.
- L2: DD + WS + PD; eletrodo 67 marcado como remoto/infinito.
- Malha quadrilateral e parâmetros idênticos aos testes individuais.
- Todas as seções invertidas usam Cut Corners.

## L1_DD_WS_COMBINADO

- Medições invertidas: 1452.
- RMS real: 1.31.
- RMS sintético: 1.12.
- IoU sintético: 0.921.

## Falhas

- L2_DD_WS_PD_COMBINADO: IndexError('index 67 is out of bounds for axis 0 with size 66')