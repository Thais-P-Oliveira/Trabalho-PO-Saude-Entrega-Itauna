"""Leitura das entradas Excel e das tabelas intermediarias em CSV."""
from pathlib import Path
import csv
import pandas as pd


def ler_tabela(caminho, **opcoes):
    caminho = Path(caminho)
    if caminho.suffix.lower() == '.xlsx':
        for chave in ['sep', 'delimiter', 'encoding', 'low_memory']:
            opcoes.pop(chave, None)
        return pd.read_excel(caminho, sheet_name='Dados', engine='openpyxl', **opcoes)
    return pd.read_csv(caminho, **opcoes)


def ler_registros(caminho, separador=';'):
    caminho = Path(caminho)
    if caminho.suffix.lower() == '.xlsx':
        return ler_tabela(caminho, dtype=str, keep_default_na=False).to_dict('records')
    with caminho.open(encoding='utf-8-sig', newline='') as arquivo:
        return list(csv.DictReader(arquivo, delimiter=separador))


def salvar_registros(caminho, linhas):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.suffix.lower() == '.xlsx':
        pd.DataFrame(linhas).to_excel(caminho, sheet_name='Dados', index=False, engine='openpyxl')
    else:
        with caminho.open('w', encoding='utf-8-sig', newline='') as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), delimiter=';')
            escritor.writeheader()
            escritor.writerows(linhas)
