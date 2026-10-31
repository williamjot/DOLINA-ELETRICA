# Relatório consolidado — inversões ERT e testes sintéticos

Data de consolidação: 31/10/2026  
Software: ResIPy 3.6.6 / R2  
Estado: **concluído e publicado na branch `main`**

## Escopo concluído

- Inversões individuais: L1-DD, L1-WS, L2-DD, L2-WS e L2-PD.
- Inversões combinadas: L1 (DD+WS) e L2 (DD+WS+PD).
- Malha quadrilateral em todos os casos.
- `Cut Corners` ativado em todas as seções invertidas.
- Forward e reinversão sintética usando exatamente os quadrupolos reais após QC.
- Polo–dipolo com eletrodo 67 explicitamente marcado como remoto/infinito.
- Cada uma das 42 novas imagens foi registrada em commit e push próprios.
- Arquivos numéricos, projetos ResIPy, CSV, DAT, VTK e logs também foram publicados.

## Pastas canônicas

| Conteúdo | Pasta |
|---|---|
| L1-DD individual já concluído anteriormente | `05_RESULTADOS_RESIPY/INVERSOES_INDIVIDUAIS_QUAD_CAVIDADE_2026-10-30/L1_DD` |
| Demais individuais | `05_RESULTADOS_RESIPY/INVERSOES_INDIVIDUAIS_QUAD_CAVIDADE_CONTINUACAO_2026-10-30` |
| L1 combinado completo | `05_RESULTADOS_RESIPY/INVERSOES_COMBINADAS_QUAD_CAVIDADE_2026-10-31/L1_DD_WS_COMBINADO` |
| L2 combinado — dados reais | `05_RESULTADOS_RESIPY/INVERSOES_COMBINADAS_QUAD_CAVIDADE_2026-10-31_L2_CONTINUACAO/L2_DD_WS_PD_COMBINADO/REAL` |
| L2 combinado — sintético final e comparação | `05_RESULTADOS_RESIPY/INVERSOES_COMBINADAS_QUAD_CAVIDADE_2026-10-31_L2_SINTETICO_FINAL` |

Os arquivos `RESUMO_GERAL.json` que registram falhas nas duas primeiras tentativas
combinadas são registros de proveniência, não o estado final. O bug interno do
ResIPy 3.6.6 ocorreu na recomputação de FMD após remover o eletrodo remoto da
tabela finita. A execução final contorna somente essa recomputação redundante,
mantendo o eletrodo 67 como `remote=True` e `x=99999` no forward R2.

## Parâmetros comuns

### Malha

- Tipo: quadrilateral.
- FMD: 120 m.
- `elemx=4`: quatro subdivisões por intervalo de eletrodo, aproximadamente 2,5 m horizontal.
- `xgf=1.5`, `zf=1.1`, `zgf=1.5`.
- `pad=8` células laterais.
- 14.520 elementos e 14.895 nós em cada caso.

### Inversão

- Resistividade em escala logarítmica (`data_type=1`).
- Inversão L2 suave (`inverse_type=1`, `reg_mode=0`).
- Regularização isotrópica (`alpha_aniso=1.0`).
- `alpha_s=10.0`.
- Máximo de 10 iterações e tolerância de 1%.
- Modelo de erro individual (`error_mod=2`) com piso de 1%.
- Limites: 1 a 1.000.000 Ω·m.
- Corte auditável de resistência de contato: `abs(cR) > 40.000 Ω`.

### Sintético

- Fundo: 5.000 Ω·m.
- Cavidade: 50.000 Ω·m.
- Contraste: 10:1.
- Ruído gaussiano: 3%.
- Semente reprodutível: 20.261.030.
- Limiar de recuperação: 15.811 Ω·m, média geométrica entre fundo e cavidade.

## Justificativa dos parâmetros

- O FMD de 120 m cobre a profundidade máxima do modelo paramétrico com margem uniforme entre perfis.
- A célula horizontal de aproximadamente 2,5 m fornece resolução compatível com o espaçamento de 10 m sem custo proibitivo.
- O padding reduz efeitos artificiais das fronteiras laterais.
- A regularização L2 suave é uma hipótese conservadora para cobertura inconsolidada e rocha alterada, sem impor contatos abruptos não demonstrados.
- A isotropia evita introduzir direção preferencial sem restrição geológica independente.
- O piso de erro impede peso infinito para leituras com erro instrumental nulo.
- O ruído de 3% testa resolução em condição não ideal sem tornar o ensaio excessivamente pessimista.
- Usar os quadrupolos reais após QC evita vantagem artificial de cobertura no ensaio sintético.

## Resultados quantitativos

| Caso | Medições | RMS real | Iter. real | RMS sintético | Iter. sint. | IoU sintético | Corr. log10 ρa real–sint. | Mediana real dentro/fora (Ω·m) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L1-DD | 651 | 1,00 | 5 | 1,00 | 2 | 0,900 | 0,128 | 2.852 / 3.783 |
| L1-WS | 801 | 1,22 | 7 | 1,07 | 2 | 0,900 | -0,073 | 3.641 / 4.770 |
| L2-DD | 819 | 1,00 | 5 | 1,26 | 2 | 0,806 | 0,353 | 13.727 / 2.480 |
| L2-WS | 895 | 1,07 | 9 | 1,00 | 3 | 0,800 | 0,334 | 17.864 / 2.435 |
| L2-PD | 1.304 | 1,08 | 6 | 1,19 | 2 | 0,848 | 0,346 | 14.492 / 2.850 |
| L1 DD+WS | 1.452 | 1,31 | 8 | 1,12 | 2 | 0,921 | 0,023 | 3.817 / 4.522 |
| L2 DD+WS+PD | 3.018 | 1,08 | 8 | 1,00 | 3 | 0,859 | 0,344 | 15.981 / 2.688 |

## Eletrodo remoto no polo–dipolo

- Eletrodo remoto: rótulo 67.
- Representação: `remote=True`, coordenada operacional `x=99999`.
- Leituras PD individuais após QC: 1.304.
- Leituras com `a=67` no forward combinado L2: 1.304.
- Total combinado L2 após QC: 819 DD + 895 WS + 1.304 PD = 3.018 medições.
- O arquivo `validacao_eletrodo_infinito.json` registra a validação tanto no real quanto no sintético.

## Interpretação

1. **Capacidade do levantamento:** os testes sintéticos recuperam a cavidade com IoU entre 0,800 e 0,921. Portanto, dadas as geometrias e o contraste adotado, os arranjos possuem capacidade teórica de detectar a estrutura.
2. **Linha L1:** a resistividade mediana dentro da cavidade modelada é menor que a região local externa em DD, WS e no combinado. A fração acima do limiar no combinado é apenas 4,6%. Assim, os dados reais de L1 não sustentam uma cavidade resistiva coincidente com o modelo paramétrico adotado.
3. **Linha L2:** DD, WS, PD e o combinado apresentam resistividade interna aproximadamente 5–7 vezes maior que a externa. No combinado, 50,2% das células da cavidade modelada excedem 15.811 Ω·m. Há evidência real de uma anomalia resistiva espacialmente compatível com a cavidade, embora isso não prove vazio aberto sem restrições independentes.
4. **Combinação de arranjos:** L1 ganha resolução sintética, mas não cria correspondência inexistente no dado real. L2 preserva o contraste observado nos três arranjos e fornece a cobertura mais completa.
5. **Correlação de dados aparentes:** as correlações real–sintético são baixas a moderadas. O modelo paramétrico explica parte da assinatura de L2, mas não toda a heterogeneidade real.

## Limitações

- O modelo de cavidade é paramétrico, não uma geometria de caverna levantada diretamente.
- O contraste 10:1 é uma hipótese de teste, não uma estimativa independente da resistividade do vazio.
- Regularização suave difunde contatos e pode ampliar ou atenuar corpos estreitos.
- A interpretação de cavidade deve ser integrada a geologia, topografia, controle de contato, investigação direta e outras informações geofísicas.

## Commits de consolidação

- `734d574`: arquivos numéricos das inversões individuais.
- `d23f214`: arquivos numéricos das inversões combinadas.
- As 42 imagens possuem commits individuais imediatamente seguidos de push.
