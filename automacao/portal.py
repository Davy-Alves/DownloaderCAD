"""Interações com o portal: Triagem, Upload e download de DWG."""
import re
import urllib.parse

from playwright.sync_api import TimeoutError

from automacao import config
from automacao.navegador import ativar_debug
from automacao.utils import sanitizar_nome

_JS_EXTRAIR_SOLICITACOES = r"""() => {
    let tds = Array.from(document.querySelectorAll('td'));
    return tds.map(td => td.innerText.trim()).filter(text => /^\d{8,12}$/.test(text));
}"""


def abrir_triagem(pagina, cliente, municipio, tentativas=3):
    """Abre a Triagem filtrada pelo cliente. Retorna False se não carregar."""
    url = (
        f"{config.URL_PORTAL}/projeto/despacho/triagem.aspx?depto=&numeroPDl="
        f"&nomeCliente={urllib.parse.quote(str(cliente))}"
        f"&nomeMunicipio={urllib.parse.quote(str(municipio))}"
        f"&codigoMunicipio=&localizacao="
    )
    for _ in range(tentativas):
        try:
            pagina.goto(url, timeout=15000)
            pagina.wait_for_timeout(2000)
            return True
        except TimeoutError:
            pagina.wait_for_timeout(2000)
    return False


def extrair_solicitacoes(pagina):
    """Retorna os Números de Solicitud da Triagem, sem repetidos e na ordem da tela."""
    numeros = pagina.evaluate(_JS_EXTRAIR_SOLICITACOES)
    return list(dict.fromkeys(numeros))


def abrir_upload(contexto, pagina_triagem, num_solicitud):
    """
    Tentativa 1: clicar no link/ícone de anexos na linha da solicitação (fluxo humano).
    Tentativa 2: abrir nova aba mandando o Referer da Triagem.
    Retorna a aba de upload.
    """
    url_triagem = pagina_triagem.url

    # --- Tentativa 1: clique real ---
    seletor = (
        f"a[href*='Slns_Codigo={num_solicitud}'], "
        f"a[onclick*='{num_solicitud}'], "
        f"img[onclick*='{num_solicitud}']"
    )
    try:
        alvo = pagina_triagem.locator(seletor).first
        if alvo.count() > 0:
            with contexto.expect_page(timeout=8000) as info:
                alvo.click()
            aba = info.value
            aba.wait_for_load_state("load")
            print("  Abrindo a solicitação no portal.")
            return aba
    except Exception:
        # Se o clique navegou na própria aba em vez de abrir popup, volta para a Triagem
        if pagina_triagem.url != url_triagem:
            pagina_triagem.go_back()
            pagina_triagem.wait_for_timeout(2000)

    # --- Tentativa 2: nova aba com Referer da Triagem ---
    url_upload = f"{config.URL_PORTAL}/Upload.aspx?numtrab=&numsob=&Slns_Codigo={num_solicitud}"
    aba = contexto.new_page()
    if config.DEBUG:
        ativar_debug(aba, "UPLOAD")
    aba.goto(url_upload, timeout=15000, referer=url_triagem)
    print("  Abrindo a solicitação em uma nova aba.")
    return aba


def localizar_links_dwg(aba):
    """Links de anexos terminados em .dwg na tela de Upload."""
    return aba.locator("a", has_text=re.compile(r"\.dwg$", re.IGNORECASE)).all()


def baixar_dwg(aba, link, pasta_destino):
    """Clica no link, salva o arquivo em pasta_destino e retorna o caminho final."""
    with aba.expect_download(timeout=30000) as info:
        link.click()
    download = info.value

    pasta_destino.mkdir(parents=True, exist_ok=True)
    caminho = pasta_destino / sanitizar_nome(download.suggested_filename)
    download.save_as(caminho)
    return caminho
