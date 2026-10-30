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
