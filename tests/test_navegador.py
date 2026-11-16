from pathlib import Path

from automacao import config, navegador
from automacao.controle import Controle
from automacao.resumo import Resumo
from tests.fakes import FakeContexto, SiteFake


class Aba:
    def __init__(self, url):
        self.url = url


class Contexto:
    def __init__(self, urls):
        self.pages = [Aba(url) for url in urls]
        self.criadas = 0

    def new_page(self):
        self.criadas += 1
        return Aba("about:blank")


def test_comando_do_chrome_nao_abre_aba_do_portal():
    """Regressão: a URL aqui criava uma aba e o Playwright abria outra igual."""
    comando = navegador.comando_do_chrome(Path("chrome.exe"), Path("perfil"))

    assert f"--remote-debugging-port={config.PORTA_CDP}" in comando
    assert all("login.aspx" not in parte for parte in comando)
    assert all(not parte.startswith(("http://", "https://")) for parte in comando)


def test_reaproveita_a_aba_em_branco_do_chrome():
    contexto = Contexto(["https://outro.exemplo/", "chrome://newtab/"])

    aba = navegador.aba_em_branco(contexto)

    assert aba is contexto.pages[1]


def test_sem_aba_em_branco_devolve_none():
    contexto = Contexto(["https://outro.exemplo/pagina"])

    assert navegador.aba_em_branco(contexto) is None


def test_aba_fechada_nao_derruba_a_procura():
    class AbaFechada:
        @property
        def url(self):
            raise RuntimeError("aba fechada")

    contexto = Contexto(["about:blank"])
    contexto.pages.insert(0, AbaFechada())

    assert navegador.aba_em_branco(contexto) is contexto.pages[1]


def test_abrir_sessao_portal_usa_uma_unica_aba():
    site = SiteFake()
    contexto = FakeContexto(site)
    inicial = contexto.new_page()  # a aba em branco que o Chrome abriu
    navegador_fake = type("NavegadorFake", (), {"contexts": [contexto]})()
    controle = Controle(Resumo(), espera=0.01)
    controle.evt_iniciar.set()

    _, pagina = navegador.abrir_sessao_portal(navegador_fake, controle)

    assert pagina is inicial
    assert len(contexto.pages) == 1
    assert pagina.url == f"{config.URL_PORTAL}/login.aspx"
