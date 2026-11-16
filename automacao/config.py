"""
Configurações do projeto.

Os padrões ficam aqui. O que é específico de cada máquina (planilha, pasta de
destino, endereço do portal, Chrome) é salvo em
%LOCALAPPDATA%\\DownloaderCAD\\config.json e sobrescreve estes valores.
Nada de senha, token ou cookie neste arquivo.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

_IGNORAR = object()


def pasta_aplicacao() -> Path:
    """Pasta do projeto (ou do .exe, quando empacotado)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = pasta_aplicacao()

# --- Configuração local (nunca vai para o Git) ------------------------------
PASTA_CONFIG_USUARIO = (
    Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    / "DownloaderCAD"
)
ARQUIVO_CONFIG_USUARIO = PASTA_CONFIG_USUARIO / "config.json"
ARQUIVO_CONFIG_EXE = BASE_DIR / "config.json"
PASTA_PERFIL_CHROME = PASTA_CONFIG_USUARIO / "chrome-perfil"
PASTA_LOGS = PASTA_CONFIG_USUARIO / "logs"

# --- Última seleção feita na janela -----------------------------------------
CAMINHO_EXCEL = None                 # Path | None
PASTA_DOWNLOADS = Path.home() / "Documents" / "CAD"

# --- Portal e navegador -----------------------------------------------------
URL_PORTAL = ""                      # obrigatório, configurado na janela
PERFIL_LOGIN = ""                    # texto opcional mostrado no login
PORTA_CDP = 9222
CDP_URL = f"http://localhost:{PORTA_CDP}"
CHROME_EXE = None                    # Path | None; None = detectar automaticamente
PERFIL_CHROME = None                 # Path | None; None = PASTA_PERFIL_CHROME

# --- Execução ---------------------------------------------------------------
LIMITE_CLIENTES = None   # None = todas as linhas pendentes; ou um número
REPROCESSAR_NAO = False  # True = refaz também as linhas marcadas "NÃO"
DEBUG = False            # imprime redirecionamentos e nomes de cookies (diagnóstico)

# --- Leitura/gravação da configuração local --------------------------------
CHAVES = {
    "planilha": ("CAMINHO_EXCEL", Path),
    "pasta_downloads": ("PASTA_DOWNLOADS", Path),
    "url_portal": ("URL_PORTAL", str),
    "perfil_login": ("PERFIL_LOGIN", str),
    "chrome_exe": ("CHROME_EXE", Path),
    "perfil_chrome": ("PERFIL_CHROME", Path),
    "porta_cdp": ("PORTA_CDP", int),
    "limite_clientes": ("LIMITE_CLIENTES", int),
    "reprocessar_nao": ("REPROCESSAR_NAO", bool),
    "debug": ("DEBUG", bool),
}

# Chaves antigas que continuam sendo aceitas na leitura.
_ALIAS = {
    "base_url": "url_portal",
}


def validar_url_portal(url) -> tuple[bool, str]:
    """Confere se o endereço do portal é utilizável."""
    texto = str(url or "").strip()
    if not texto:
        return False, "Configure o endereço do portal em Configurações."
    partes = urlparse(texto)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return False, "O endereço do portal deve começar com http:// ou https://."
    return True, ""


def _ler_json(caminho: Path) -> dict:
    if not caminho.is_file():
        return {}
    try:
        # utf-8-sig aceita o config.json salvo com BOM (Notepad/PowerShell).
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ValueError(f"configuração inválida em {caminho}: {erro}") from erro
    if not isinstance(dados, dict):
        raise ValueError(f"configuração inválida em {caminho}: o conteúdo deve ser um objeto JSON.")
    return dados


def ler_config() -> dict:
    """Lê o config.json ao lado do .exe e o do usuário (este sobrescreve)."""
    dados = {}
    dados.update(_ler_json(ARQUIVO_CONFIG_EXE))
    dados.update(_ler_json(ARQUIVO_CONFIG_USUARIO))
    for antigo, novo in _ALIAS.items():
        if antigo in dados and novo not in dados:
            dados[novo] = dados[antigo]
    return {chave: valor for chave, valor in dados.items() if chave in CHAVES}


def _converter(chave: str, valor, tipo):
    if chave == "url_portal":
        return str(valor or "").strip().rstrip("/")
    if chave == "perfil_login":
        return str(valor or "").strip()

    if chave in ("chrome_exe", "perfil_chrome"):
        if valor in (None, ""):
            return None
        return Path(str(valor)).expanduser()

    if valor in (None, ""):
        if chave == "limite_clientes":
            return None
        return _IGNORAR

    if tipo is Path:
        return Path(str(valor)).expanduser()

    if tipo is int:
        try:
            numero = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"o campo '{chave}' deve ser um número inteiro.") from erro
        if chave == "limite_clientes" and numero < 1:
            raise ValueError("o campo 'limite_clientes' deve ser vazio ou um número maior que zero.")
        if chave == "porta_cdp" and not (1 <= numero <= 65535):
            raise ValueError("o campo 'porta_cdp' deve estar entre 1 e 65535.")
        return numero

    if tipo is bool:
        if isinstance(valor, bool):
            return valor
        texto = str(valor).strip().lower()
        if texto in ("1", "true", "sim", "yes"):
            return True
        if texto in ("0", "false", "nao", "não", "no"):
            return False
        raise ValueError(f"o campo '{chave}' deve ser true ou false.")

    if tipo is str:
        return str(valor).strip().rstrip("/")

    return valor


def aplicar_config(dados: dict) -> None:
    """Aplica os valores lidos às variáveis do módulo."""
    global CDP_URL
    modulo = sys.modules[__name__]
    for chave, valor in dados.items():
        if chave not in CHAVES:
            continue
        nome, tipo = CHAVES[chave]
        convertido = _converter(chave, valor, tipo)
        if convertido is _IGNORAR:
            continue
        setattr(modulo, nome, convertido)
    CDP_URL = f"http://localhost:{PORTA_CDP}"


def carregar_config() -> dict:
    """Lê e aplica a configuração local. Levanta ValueError se o JSON for inválido."""
    dados = ler_config()
    aplicar_config(dados)
    return dados


def _serializar(valor):
    if isinstance(valor, Path):
        return str(valor)
    return valor


def salvar_config(**campos) -> None:
    """Grava apenas as chaves conhecidas no config.json do usuário."""
    dados = ler_config()
    for chave, valor in campos.items():
        if chave in CHAVES:
            dados[chave] = _serializar(valor)
    PASTA_CONFIG_USUARIO.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO_CONFIG_USUARIO.with_suffix(".json.tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, ARQUIVO_CONFIG_USUARIO)


def caminho_perfil_chrome() -> Path:
    """Perfil dedicado do Chrome (cookies da sessão ficam só nesta máquina)."""
    return Path(PERFIL_CHROME) if PERFIL_CHROME else PASTA_PERFIL_CHROME
