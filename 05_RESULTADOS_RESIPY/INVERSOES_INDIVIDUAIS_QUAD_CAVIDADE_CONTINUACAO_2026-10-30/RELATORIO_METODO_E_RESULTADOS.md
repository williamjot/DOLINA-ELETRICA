# Inversões individuais quadrilaterais e teste sintético de cavidade

Execução: 2026-10-30T23:49:30
ResIPy: 3.6.6
Pandas: 2.3.3

## Parâmetros comuns

- Malha: quadrilateral; FMD=120.0 m; elemx=4; xgf=1.5; zf=1.1; zgf=1.5; pad=8.
- Inversão: log-resistividade; L2 suave; isotrópica; até 10 iterações; tolerância=1.0%; erro individual com piso de 1.0%.
- Limites de resistividade: 1 a 1e+06 ohm.m.
- Sintético: fundo=5000 ohm.m; cavidade=50000 ohm.m; ruído gaussiano=3.0%.
- Todas as seções invertidas usam `clipCorners=True` (Cut Corners).

## Justificativa

- FMD de 120 m cobre os 105 m do modelo paramétrico com margem e mantém comparação uniforme entre arranjos.
- Quatro subdivisões por intervalo de 10 m fornecem células horizontais próximas de 2,5 m sem custo excessivo.
- O padding de 8 células (duas vezes `elemx`) reduz influência das fronteiras laterais.
- A inversão L2 suave é a hipótese mínima para cobertura inconsolidada/rocha alterada sem impor contatos abruptos não demonstrados.
- A isotropia evita introduzir direção preferencial sem informação geológica independente.
- O piso de erro de 1% impede que leituras com erro instrumental igual a zero recebam peso infinito.
- O contraste sintético 10:1 é conservador para uma cavidade resistiva e permanece dentro da faixa observada nas inversões existentes.
- O ruído de 3% testa detectabilidade em condição não ideal; a semente fixa torna o ensaio reproduzível.
- A sequência sintética é exatamente a sequência real após QC de cada arranjo, evitando vantagem de cobertura artificial.

## Resultados

### L1_WS

- Medições reais invertidas: 801.
- RMS real: 1.22; iterações: 7.
- RMS sintético: 1.07; iterações: 2.
- IoU sintético: 0.900; recall: 0.976; precisão: 0.921.
- Correlação log10(ρa) real–sintético: -0.073.
- Mediana real dentro/fora da cavidade modelada: 3641 / 4770 ohm.m.

### L2_DD

- Medições reais invertidas: 819.
- RMS real: 1.0; iterações: 5.
- RMS sintético: 1.26; iterações: 2.
- IoU sintético: 0.806; recall: 0.896; precisão: 0.889.
- Correlação log10(ρa) real–sintético: 0.353.
- Mediana real dentro/fora da cavidade modelada: 13727 / 2480 ohm.m.

### L2_WS

- Medições reais invertidas: 895.
- RMS real: 1.07; iterações: 9.
- RMS sintético: 1.0; iterações: 3.
- IoU sintético: 0.800; recall: 0.848; precisão: 0.935.
- Correlação log10(ρa) real–sintético: 0.334.
- Mediana real dentro/fora da cavidade modelada: 17864 / 2435 ohm.m.

### L2_PD

- Medições reais invertidas: 1304.
- RMS real: 1.08; iterações: 6.
- RMS sintético: 1.19; iterações: 2.
- IoU sintético: 0.848; recall: 0.860; precisão: 0.984.
- Correlação log10(ρa) real–sintético: 0.346.
- Mediana real dentro/fora da cavidade modelada: 14492 / 2850 ohm.m.
