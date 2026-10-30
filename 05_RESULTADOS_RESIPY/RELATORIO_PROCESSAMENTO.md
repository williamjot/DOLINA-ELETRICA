# Processamento e inversão ResIPy — Dolina dos Maracanãs

Data de execução: 2026-10-30 16:52:05

## Metodologia

- ResIPy 3.6.6, projeto 2D R2.
- Arquivos Syscal `.bin` já filtrados foram importados e combinados por linha.
- Topografia aplicada por eletrodo a partir das planilhas X, Y, Z, sem cabeçalho no arquivo de intercâmbio.
- Malha triangular gerada pelo Gmsh com a topografia incorporada.
- Inversão logarítmica regularizada com parâmetros padrão do ResIPy/R2 e pesos instrumentais `magErr`.
- Foram removidos apenas registros não finitos, com resistividade aparente não positiva ou resistência nula.
- Filtros de reciprocidade e dados sem par não foram aplicados porque não existem recíprocos nos arquivos.
- O filtro `filterNegative()` não foi aplicado porque DD/PD apresentam resistência de transferência negativa por convenção geométrica, com resistividade aparente positiva.

## Por que os arranjos foram combinados

Foi feita uma inversão conjunta por linha física, não uma mistura entre linhas. Os arranjos de uma mesma linha compartilham o mesmo estaqueamento e a mesma topografia, mas têm sensibilidades complementares: DD melhora a resolução lateral, WS amplia a cobertura e PD acrescenta sensibilidade em profundidade. A origem de cada leitura permanece identificada em `dados_combinados_qc.csv`, permitindo auditoria e eventual comparação por arranjo.

## Resultados

### L1_2026-10-22_COMBINADO_DD_WS

- Medições invertidas: 1478
- Composição: DD 667 + WS 811
- Eletrodos topográficos: 66
- Faixa de cota: 889.52 a 905.15 m
- Elementos da malha: 33412
- RMS final informado pelo ResIPy: 1.1
- Iterações: 9
- Convergência: True

### L2_2026-10-24_COMBINADO_DD_PD_WS

- Medições invertidas: 3062
- Composição: DD 828 + WS 913 + PD 1321
- Eletrodos topográficos: 66
- Faixa de cota: 886.45 a 898.01 m
- Elementos da malha: 54144
- RMS final informado pelo ResIPy: 1.04
- Iterações: 8
- Convergência: True

## Validação final

- Linha 1: 15000 células de resultado; resistividade de 205.77 a 42348.34 ohm.m; nenhum valor inválido.
- Linha 2: 30786 células de resultado; resistividade de 308.35 a 81861.30 ohm.m; nenhum valor inválido.
- As duas seções foram inspecionadas visualmente; topografia, eletrodos e domínio da malha foram renderizados corretamente.

## Conteúdo de cada pasta de perfil

- `04_modelo_resistividade.png`: seção de resistividade invertida.
- `resultado_csv/` e `resultado_vtk/`: malha e valores numéricos para análise externa.
- `dados_combinados_qc.csv`: quadrupolos efetivamente usados.
- `topografia_eletrodos.csv`: topografia aplicada.
- `R2.out` e `historico_iteracoes.csv`: registro de convergência.
- `.resipy`: projeto reabrível no ResIPy.
