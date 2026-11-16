"""Conexão com o Chrome, abertura automática, sessão do portal e utilidades de abas."""
import socket
import subprocess
import time
from pathlib import Path

from automacao import config


def encontrar_chrome() -> Path | None:
    """Procura o chrome.exe no registro e nos caminhos padrão do Windows."""
    candidatos = []
    if config.CHROME_EXE:
        candidatos.append(Path(config.CHROME_EXE))

    try:
        import winreg
        for raiz in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            chave = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
            try:
                with winreg.OpenKey(raiz, chave) as aberta:
                    valor, _ = winreg.QueryValueEx(aberta, "")
                    candidatos.append(Path(valor))
            except OSError:
                pass
    except ImportError:
        pass

    candidatos += [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]

    for caminho in candidatos:
        try:
            if caminho.is_file():
                return caminho
        except OSError:
            pass
    return None


def porta_cdp_aberta(porta: int | None = None) -> bool:
    """True se já existe um Chrome escutando na porta de depuração."""
    porta = porta or config.PORTA_CDP
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
            return True
    except OSError:
        return False


def comando_do_chrome(chrome: Path, perfil: Path) -> list[str]:
    """Argumentos para abrir o Chrome dedicado, sem nenhuma URL.

    Quem abre a aba do portal é `abrir_sessao_portal`. Passar a URL aqui
    abria uma aba na linha de comando e outra no Playwright: duas abas iguais.
    """
    return [
        str(chrome),
        f"--remote-debugging-port={config.PORTA_CDP}",
        f"--user-data-dir={perfil}",
        "--no-first-run",
        "--no-default-browser-check",
    ]


def garantir_chrome_aberto(espera: float = 15.0) -> Path | None:
    """
    Abre o Chrome com --remote-debugging-port se ele ainda não estiver aberto.
    Usa um perfil dedicado (%LOCALAPPDATA%\\DownloaderCAD\\chrome-perfil), para
    não mexer no Chrome normal do usuário e manter o login entre execuções.
    """
    if porta_cdp_aberta():
        return None

    valido, mensagem = config.validar_url_portal(config.URL_PORTAL)
    if not valido:
        raise RuntimeError(mensagem)

    chrome = encontrar_chrome()
    if chrome is None:
        raise RuntimeError(
            "Não encontrei o Google Chrome. Instale o Chrome ou informe o caminho "
            "em Configurações (campo Chrome)."
        )

    perfil = config.caminho_perfil_chrome()
    perfil.mkdir(parents=True, exist_ok=True)

    comando = comando_do_chrome(chrome, perfil)
    subprocess.Popen(comando, close_fds=True)

    limite = time.time() + espera
    while time.time() < limite:
        if porta_cdp_aberta():
            return chrome
        time.sleep(0.5)

    raise RuntimeError(
        "O Chrome foi aberto, mas a porta de depuração não respondeu. "
        "Feche as janelas do Chrome do Downloader CAD e tente de novo."
    )


def conectar_chrome(playwright):
    """Conecta ao Chrome aberto com --remote-debugging-port."""
    return playwright.chromium.connect_over_cdp(config.CDP_URL)


def aba_em_branco(contexto):
    """Aba inicial que o Chrome abriu (nova guia/em branco), se ainda existir.

    Reaproveitá-la evita a segunda aba vazia ao lado da aba do portal.
    """
    for pagina in contexto.pages:
        try:
            url = pagina.url or ""
        except Exception:
            continue
        if url in ("about:blank", "") or url.startswith(("chrome://newtab", "chrome://welcome")):
            return pagina
    return None


def abrir_sessao_portal(navegador, controle):
    """
    Usa o Chrome real: o login e a escolha do perfil são feitos À MÃO.
    Espera o clique em "Já estou logado" na janela.
    Retorna (contexto, pagina).
    """
    if not navegador.contexts:
        raise RuntimeError("O Chrome abriu sem um contexto utilizável. Feche-o e tente de novo.")

    contexto = navegador.contexts[0]
    # Reaproveita a aba em branco da abertura do Chrome; só cria outra se não houver.
    pagina = aba_em_branco(contexto) or contexto.new_page()
    try:
        pagina.bring_to_front()
    except Exception:
        pass

    pagina.goto(f"{config.URL_PORTAL}/login.aspx")

    print("\n==================================================")
    print("Na aba do portal que abriu no Chrome:")
    print("  1. Faça login")
    print("  2. Escolha o perfil de acesso, se aparecer")
    if config.PERFIL_LOGIN:
        print(f"     Perfil configurado: {config.PERFIL_LOGIN}")
    print("  3. Espere carregar a tela inicial")
    print("  4. Na janela do Downloader CAD, clique em 'Já estou logado'")
    print("==================================================")

    controle.set(estado="aguardando_login")
    controle.aguardar_inicio()
    controle.set(estado="executando", inicio=time.time())

    if config.DEBUG:
        ativar_debug(pagina, "TRIAGEM")
        mostrar_cookies(contexto, "APÓS LOGIN")

    return contexto, pagina


def sessao_caiu(pagina, trecho_url_esperado):
    """
    Considera a sessão caída se:
      - a página foi redirecionada para logout/login;
      - a URL não é mais a da tela esperada (triagem.aspx / upload.aspx);
      - o texto da página indica sessão expirada.
    """
    url = pagina.url.lower()
    if "logout.aspx" in url or "login.aspx" in url:
        return True
    if trecho_url_esperado not in url:
        return True
    try:
        texto = pagina.inner_text("body", timeout=3000).lower()
    except Exception:
        return False
    marcadores = ("sessão expirada", "sessao expirada", "sessão expirou", "sessao expirou", "session expired")
    return any(m in texto for m in marcadores)


def limpar_abas(contexto, pagina_principal):
    """Fecha abas about:blank deixadas pelos popups de download (não toca nas demais abas)."""
    for aba in list(contexto.pages):
        try:
            if aba != pagina_principal and not aba.is_closed() and aba.url in ("about:blank", ""):
                aba.close()
        except Exception:
            pass


def ativar_debug(pagina, rotulo):
    """Mostra no terminal a cadeia de respostas/redirecionamentos de uma aba."""
    def on_response(r):
        if r.request.resource_type == "document":
            destino = r.headers.get("location", "")
            print(f"   [{rotulo}] [{r.status}] {r.url}" + (f" -> {destino}" if destino else ""))

    def on_nav(frame):
        if frame == pagina.main_frame:
            print(f"   [{rotulo}] [NAV] {frame.url}")

    pagina.on("response", on_response)
    pagina.on("framenavigated", on_nav)


def mostrar_cookies(contexto, momento):
    """Imprime os nomes dos cookies (sem os valores, para não vazar a sessão)."""
    if not config.DEBUG:
        return
    cookies = contexto.cookies()
    nomes = [f"{c['name']}(path={c['path']})" for c in cookies]
    print(f"   [COOKIES {momento}] {nomes}")
