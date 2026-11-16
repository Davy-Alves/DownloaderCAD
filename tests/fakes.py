"""
Dublês do Playwright e do portal para os testes.

Nenhum teste fala com o site real: o "oráculo" aqui é o comportamento esperado
descrito em cada teste (entrada conhecida -> resultado esperado).
"""
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

BASE_URL = "https://portal.exemplo.invalid"


@dataclass
class SiteFake:
    """Descreve o que o portal 'responde' em cada cenário."""
    solicitacoes: dict = field(default_factory=dict)    # cliente -> [números de solicitud]
    dwgs: dict = field(default_factory=dict)            # solicitud -> [nomes de arquivo .dwg]
    cai_na_triagem: set = field(default_factory=set)    # clientes cuja Triagem derruba a sessão
    cai_no_upload: set = field(default_factory=set)     # solicitudes cujo Upload derruba a sessão
    falha_no_upload: set = field(default_factory=set)   # solicitudes cujo Upload dá erro de rede


class FakeLocator:
    def __init__(self, itens=None):
        self.itens = itens or []

    @property
    def first(self):
        return self

    def count(self):
        return len(self.itens)

    def all(self):
        return list(self.itens)


class FakeDownload:
    def __init__(self, nome):
        self.suggested_filename = nome

    def save_as(self, caminho):
        Path(caminho).write_bytes(b"dwg")


class FakeExpectDownload:
    def __init__(self, aba):
        self.aba = aba

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def value(self):
        return FakeDownload(self.aba.ultimo_click)


class FakeLink:
    def __init__(self, nome, aba):
        self.nome, self.aba = nome, aba

    def inner_text(self):
        return f"  {self.nome} "

    def click(self):
        self.aba.ultimo_click = self.nome


class FakePagina:
    def __init__(self, site):
        self.site = site
        self.url = "about:blank"
        self.fechada = False
        self.ultimo_click = None

    @staticmethod
    def _param(url, nome):
        return urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get(nome, [""])[0]

    def goto(self, url, timeout=None, referer=None):
        if "triagem.aspx" in url and self._param(url, "nomeCliente") in self.site.cai_na_triagem:
            self.url = f"{BASE_URL}/logout.aspx"
        elif "Upload.aspx" in url:
            codigo = self._param(url, "Slns_Codigo")
            if codigo in self.site.falha_no_upload:
                raise RuntimeError("erro de rede simulado")
            self.url = f"{BASE_URL}/logout.aspx" if codigo in self.site.cai_no_upload else url
        else:
            self.url = url

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, js):
        cliente = self._param(self.url, "nomeCliente")
        numeros = list(self.site.solicitacoes.get(cliente, []))
        return numeros + numeros[:1]  # repetido de propósito: o código deve deduplicar

    def inner_text(self, seletor, timeout=None):
        return ""

    def locator(self, seletor, **kw):
        if seletor == "a":  # links de DWG na tela de Upload
            codigo = self._param(self.url, "Slns_Codigo")
            return FakeLocator([FakeLink(n, self) for n in self.site.dwgs.get(codigo, [])])
        return FakeLocator([])  # sem link clicável na Triagem -> usa a abertura por nova aba

    def expect_download(self, timeout=None):
        return FakeExpectDownload(self)

    def is_closed(self):
        return self.fechada

    def close(self):
        self.fechada = True


class FakeContexto:
    def __init__(self, site):
        self.site = site
        self.pages = []

    def new_page(self):
        pagina = FakePagina(self.site)
        self.pages.append(pagina)
        return pagina
