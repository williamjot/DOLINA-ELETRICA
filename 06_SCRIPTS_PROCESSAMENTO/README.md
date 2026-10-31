# Scripts de processamento

## Reinversão com corte de contato de 40 kΩ

O fluxo preserva os `.bin` originais, combina os arranjos por linha, aplica o
corte por medição `abs(cR) > 40.000 Ω`, registra todas as exclusões e executa
novas inversões R2 com a topografia dos 66 eletrodos.

No PowerShell:

```powershell
python -m venv resipy-env
.\resipy-env\Scripts\python.exe -m pip install -r .\requirements_resipy.txt
.\reinverter_contato_40k.ps1 -RaizDados 'C:\caminho\DOLINA DOS MARACANAS' -Saida 'C:\caminho\nova_saida'
```

O script se recusa a sobrescrever uma pasta de saída existente. Para repetir
o processamento, informe uma nova pasta com `-Saida`.

Arquivos principais:

- `process_dolina_resipy.py`: processamento, auditoria, malha, inversão e exportações.
- `reinverter_contato_40k.ps1`: comando de execução com limite padrão de 40.000 Ω.
- `analisar_resistencia_contato.py`: diagnóstico dos dados brutos e filtrados.
- `organizar_dolina.ps1`: organização inicial do acervo.

O ResIPy 3.6.6 foi a versão usada nos resultados publicados.

## Inversões individuais quadrilaterais e ensaio sintético

`resipy_individual_quad_synthetic.py` executa separadamente `L1-DD`, `L1-WS`,
`L2-DD`, `L2-WS` e `L2-PD`, com corte auditável de contato em 40 kΩ, malha
quadrilateral e `Cut Corners` (`clipCorners=True`) nas seções exportadas.

O mesmo script constrói no ResIPy um modelo direto de cavidade resistiva a
partir de `dolina_model.npz`, usa exatamente os quadrupolos reais de cada
arranjo, adiciona ruído gaussiano reprodutível e reinverte os dados sintéticos
a partir de um fundo homogêneo. Parâmetros, métricas e justificativas são
gravados em JSON e Markdown na pasta de saída.

Exemplo:

```powershell
python .\resipy_individual_quad_synthetic.py `
  'D:\WILLIAM\DOLINA-ELETRICA' `
  'D:\WILLIAM\DOLINA-ELETRICA\05_RESULTADOS_RESIPY\INVERSOES_INDIVIDUAIS_QUAD_CAVIDADE'
```

O ResIPy 3.6.6 requer `pandas<3`; essa restrição está fixada em
`requirements_resipy.txt`.

`resipy_combined_quad_synthetic.py` repete o mesmo método com os arranjos
combinados por linha: DD+WS em L1 e DD+WS+PD em L2. No caso L2, o eletrodo 67
é validado e marcado como remoto (`remote=True`), que é a representação do
eletrodo no infinito usada pelo R2/ResIPy.

Os dois scripts aceitam `--publish-images`. Quando essa opção é usada, cada
PNG é adicionado isoladamente a um commit e enviado imediatamente para
`origin/main`. Os arquivos numéricos permanecem fora desses commits e devem
ser registrados em um commit final após a validação da execução.

## Notebooks prontos para execução manual

Os notebooks em `notebooks/` são entregues sem células executadas e nunca
retomam automaticamente pastas parciais:

- `01_secoes_brutas_iniciais_ERT.ipynb`: cinco seções brutas individuais e
  duas combinadas, diretamente dos arquivos `BRUTOS`.
- `02_inversoes_individuais_quad_sintetico.ipynb`: seleção explícita dos casos,
  inversões quadrilaterais e ensaio sintético no ResIPy.
- `03_continuacao_individuais_e_combinados.ipynb`: continuação dos quatro casos
  individuais pendentes e, depois, os dois perfis com arranjos combinados.

Ambos recusam sobrescrever uma pasta de saída existente.
