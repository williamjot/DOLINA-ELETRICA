# Verificação de resistência de contato — Dolina dos Maracanãs

Data da análise: 30/10/2026

## Conclusão

O limite solicitado de **40 kΩ** corresponde a **40.000 Ω** na coluna `cR` do ResIPy. Os arquivos Syscal registram `RsChk` em kΩ e o parser do ResIPy converte o valor para Ω.

Os arquivos já denominados `FILTRADO` ainda contêm **70 medições acima de 40 kΩ**. A aplicação do corte reduz o conjunto combinado de **4.540 para 4.470 medições**. O corte deve ser feito por medição (`cR > 40.000 Ω`), e não removendo automaticamente todo quadrupolo que utiliza um eletrodo suspeito.

Nos arquivos multicanal analisados, `RsChk` varia com o dipolo receptor M–N. Os números físicos dos eletrodos foram recuperados pela coordenada da estação (`x/10 + 1`), evitando a renumeração interna que ocorre quando eletrodos desaparecem de um arquivo filtrado.

## Cruzamento com as seções

- **Linha 1:** as feições superficiais próximas de 190–210 m e 520–590 m coincidem com pares M–N de contato muito alto. Parte das feições rasas nessa região pode estar contaminada por contato ruim.
- **Linha 1, setor 350–450 m:** existe resistividade elevada, mas somente o par 40–41 está ligeiramente acima do corte (aprox. 41,9 kΩ no DD). O corpo profundo não deve ser atribuído integralmente ao contato.
- **Linha 2:** os contatos problemáticos estão no início da linha (20–30 m) e em 150–160 m. O corpo resistivo profundo centrado perto de 350 m não coincide espacialmente com esses contatos e não parece ser um artefato de resistência de contato.

## Eletrodos e pares prioritários

### Linha 1

1. **Eletrodo 21 — estação 200 m:** prioridade máxima. Os pares 20–21 e 21–22 atingem 999,99 kΩ nos arranjos DD e WS. O eletrodo 21 é o elemento comum.
2. **Eletrodos 54 e 55 — estações 530–540 m:** prioridade máxima. Os pares 53–54, 54–55 e 55–56 são altos nos dois arranjos; o conjunto indica problema nos eletrodos/take-outs 54–55 ou nessa parte do cabo.
3. **Eletrodo 58 — estação 570 m:** prioridade máxima. Os pares 57–58 e 58–59 são altos no DD e WS; o eletrodo 58 é o elemento comum.
4. **Setor 590–610 m e par 65–66:** aparecem saturados no DD, mas não se repetem da mesma forma no WS. Tratar primeiro como falha de bloco/canal/cabo do levantamento DD, sem condenar um único eletrodo.
5. **Par 40–41 — 390–400 m:** caso limítrofe, 41,87–42,14 kΩ no DD. Deve sair se o corte for estritamente `>40 kΩ`.

Nos brutos da Linha 1 existem 412 medições acima do limite; a filtragem anterior removeu a maior parte, mas restaram 26.

### Linha 2

1. **Eletrodo 3 — estação 20 m:** forte suspeito. Os pares 2–3 e 3–4 apresentam 60–74 kΩ em DD/WS/PD. O eletrodo 3 é o elemento comum.
2. **Par 16–17 — estações 150–160 m:** 43–47 kΩ de forma sistemática nos três arranjos. Como 15–16 e 17–18 permanecem abaixo de 40 kΩ, não é possível culpar apenas o eletrodo 16 ou 17; conferir ambos, os take-outs e o trecho de cabo.
3. **Par 21–22:** apenas um valor marginal de 41,77 kΩ no WS; baixa prioridade.

Nos brutos da Linha 2 existem 54 medições acima do limite; 44 ainda permanecem nos arquivos filtrados.

## Impacto do corte nos arquivos filtrados

| Linha | Arranjo | Antes | Remover >40 kΩ | Depois |
|---|---:|---:|---:|---:|
| L1 | DD | 667 | 16 | 651 |
| L1 | WS | 811 | 10 | 801 |
| L2 | DD | 828 | 9 | 819 |
| L2 | WS | 913 | 18 | 895 |
| L2 | PD | 1.321 | 17 | 1.304 |
| **Total** |  | **4.540** | **70** | **4.470** |

## Como aplicar no ResIPy

Aplicar depois da importação dos `.bin` filtrados e antes da geração da malha/inversão:

```python
removidas = project.filterContRes(vmax=40000)
print(removidas)
```

O método trabalha na unidade da coluna `cR`, que neste caso é Ω. A lista completa das medições a remover está em `medicoes_filtradas_a_remover_40k.csv`.

Não foi realizada uma nova inversão nesta etapa. Os arquivos originais e filtrados não foram modificados.

## Arquivos auxiliares

- `01_resistencia_contato_bruta_por_posicao.png`: valores brutos por posição do dipolo M–N.
- `02_ranking_eletrodos_contato.png`: recorrência de contato alto por eletrodo.
- `03_impacto_corte_40k_filtrados.png`: quantidade removida em cada arranjo.
- `resumo_por_arquivo.csv`: estatísticas dos dez arquivos.
- `pares_contato_brutos.csv`: estatísticas por par de contato M–N.
- `ranking_eletrodos_brutos.csv`: evidência por eletrodo físico.
- `medicoes_acima_40k.csv`: todas as medições brutas e filtradas acima do limite.
- `medicoes_filtradas_a_remover_40k.csv`: somente as 70 medições ainda presentes nos arquivos filtrados.

## Referências técnicas

- IRIS Instruments — Rs Check em kΩ: https://download.iris-instruments.com/Documents/Test_box_syscal.pdf
- ResIPy API — filtro de resistência de contato: https://resipy.org/api.html
