"""Leitura da planilha de controle e gravação da coluna CAD."""
from dataclasses import dataclass

import pandas as pd
from openpyxl import load_workbook


@dataclass(frozen=True)
class LinhaPendente:
    """Uma linha da planilha que ainda precisa ser processada."""
    linha_excel: int
    cliente: str
    ordem: str
    municipio: str


class Planilha:
    """
    Abre o Excel com openpyxl (preserva formatação, tabela e filtros) e
    controla a coluna "CAD".
    """

    def __init__(self, caminho):
        self.caminho = caminho
        self.wb = load_workbook(caminho)
        self.ws = self.wb.worksheets[0]  # mesma aba que o pandas lê por padrão
        self.linha_cab, self.col_cad = self._localizar_coluna_cad()

    def _localizar_coluna_cad(self):
        for linha in range(1, 21):
            for celula in self.ws[linha]:
                if isinstance(celula.value, str) and celula.value.strip().upper() == "CAD":
                    return linha, celula.column
        raise ValueError('não encontrei uma coluna chamada "CAD" na planilha.')

    def _ja_preenchida(self, linha_excel, reprocessar_nao=False):
        valor = self.ws.cell(row=linha_excel, column=self.col_cad).value
        if valor is None:
            return False
        texto = str(valor).strip().upper()
        if texto == "":
            return False
        if reprocessar_nao and texto in ("NÃO", "NAO"):
            return False
        return True

    def carregar_dataframe(self):
        """Lê a planilha com pandas usando a mesma linha de cabeçalho do openpyxl."""
        return pd.read_excel(self.caminho, header=self.linha_cab - 1)

    def carregar_pendentes(self, reprocessar_nao=False, df=None):
        """
        Retorna (pendentes, qtd_ja_preenchidas).

        Pendentes = linhas com cliente e ordem válidos e a célula CAD vazia.
        Assim, ao reiniciar, o robô pula o que já foi marcado e continua de onde parou
        (e ainda refaz linhas que ficaram em branco por erro).

        `df` permite reaproveitar a leitura já feita pela validação do formato.
        """
        if df is None:
            df = self.carregar_dataframe()
        pendentes = []
        ja_preenchidas = 0

        for index, row in df.iterrows():
            ordem = row.get("SOLICITACAO")
            cliente = row.get("Nome do cliente")
            if pd.isna(ordem) or pd.isna(cliente):
                continue

            linha_excel = self.linha_cab + 1 + index
            if self._ja_preenchida(linha_excel, reprocessar_nao):
                ja_preenchidas += 1
                continue

            municipio = row.get("MUNICIPIO")
            pendentes.append(LinhaPendente(
                linha_excel=linha_excel,
                cliente=str(cliente),
                ordem=str(ordem),
                municipio="" if pd.isna(municipio) else str(municipio),
            ))

        return pendentes, ja_preenchidas

    def gravar_cad(self, linha_excel, valor):
        """Grava SIM/NÃO na célula CAD da linha e salva o arquivo."""
        self.ws.cell(row=linha_excel, column=self.col_cad, value=valor)
        self.salvar()

    def salvar(self):
        try:
            self.wb.save(self.caminho)
            return True
        except PermissionError:
            print("  AVISO: não consegui salvar a planilha. Ela pode estar aberta "
                  "no Excel. Feche o arquivo; tento salvar de novo no próximo cliente.")
            return False
