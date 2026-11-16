"""Funções utilitárias sem dependência do resto do projeto."""
import re

import pandas as pd


def sanitizar_nome(nome) -> str:
    """Troca caracteres proibidos em nomes de pasta/arquivo do Windows por '-'."""
    if pd.isna(nome):
        return "DESCONHECIDO"
    return re.sub(r'[\\/:*?"<>|]', '-', str(nome).strip())
