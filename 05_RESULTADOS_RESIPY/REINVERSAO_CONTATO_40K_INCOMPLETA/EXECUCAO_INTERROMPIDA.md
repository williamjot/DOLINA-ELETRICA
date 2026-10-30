# Reinversão com corte de contato — execução interrompida

Data: 30/10/2026

Esta pasta contém uma execução **parcial** da reinversão com o critério
`abs(cR) <= 40.000 Ω`. O processamento foi interrompido a pedido do usuário e
não deve ser tratado como resultado final de inversão.

## Estado preservado

- Linha 1 importada e auditada.
- 26 medições removidas por contato: 16 DD e 10 WS.
- 1.452 medições encaminhadas ao R2.
- Malha triangular com 33.412 elementos criada.
- Solver interrompido durante a iteração 8, antes da convergência final, das
  exportações finais e da criação do projeto `.resipy` consolidado.
- Linha 2 não iniciada nesta execução.

Os arquivos `auditoria_corte_contato_40k.csv` e
`dados_removidos_contato_40k.csv` são válidos como trilha do corte da Linha 1.
Os arquivos dentro de `projeto_resipy/invdir` são intermediários e servem
somente para diagnóstico/reprodutibilidade da interrupção.

Para executar novamente desde o início, use
`06_SCRIPTS_PROCESSAMENTO/reinverter_contato_40k.ps1` no repositório e escolha
uma nova pasta de saída.
