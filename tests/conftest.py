import pytest
from openpyxl import Workbook, load_workbook

from automacao import config
from automacao.controle import Controle
from automacao.planilha import Planilha
from automacao.resumo import Resumo

from tests.fakes import FakeContexto, FakePagina, SiteFake


@pytest.fixture(autouse=True)
def ambiente_isolado(tmp_path, monkeypatch):
    """Nenhum teste toca na planilha real nem na pasta de destino real."""
    destino = tmp_path / "downloads"
    destino.mkdir()
    monkeypatch.setattr(config, "PASTA_DOWNLOADS", destino)
    monkeypatch.setattr(config, "CAMINHO_EXCEL", tmp_path / "base.xlsx")
    monkeypatch.setattr(config, "PASTA_LOGS", tmp_path / "logs")
    monkeypatch.setattr(config, "URL_PORTAL", "https://portal.exemplo.invalid")
    monkeypatch.setattr(config, "DEBUG", False)


@pytest.fixture
def criar_planilha(tmp_path):
    """Cria uma planilha de teste: cabeçalho na linha 2 e coluna CAD na D."""
    def _criar(linhas):
        caminho = tmp_path / "base.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["Título qualquer"])
        ws.append(["SOLICITACAO", "Nome do cliente", "MUNICIPIO", "CAD"])
        for linha in linhas:
            ws.append(list(linha))
        wb.save(caminho)
        return caminho
    return _criar


@pytest.fixture
def ler_cad():
    """Lê a coluna CAD direto do arquivo salvo (o que o usuário veria no Excel)."""
    def _ler(caminho, linha):
        return load_workbook(caminho).worksheets[0].cell(row=linha, column=4).value
    return _ler


@pytest.fixture
def cenario(criar_planilha, tmp_path):
    """Monta planilha + site fake + controlador e devolve os dados da execução."""
    def _montar(linhas, site=None):
        site = site or SiteFake()
        caminho = criar_planilha(linhas)
        planilha = Planilha(caminho)
        pendentes, ja = planilha.carregar_pendentes()
        resumo = Resumo()
        controle = Controle(
            resumo,
            historico_path=tmp_path / "logs" / "alteracoes.csv",
            espera=0.01,
        )
        controle.set(ja_preenchidas=ja, total_geral=ja + len(pendentes), concluidos=ja)
        return {
            "caminho": caminho, "planilha": planilha, "pendentes": pendentes, "resumo": resumo,
            "controle": controle, "contexto": FakeContexto(site), "pagina": FakePagina(site),
        }
    return _montar
