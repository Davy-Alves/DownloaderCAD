"""Garante que nenhum dado da empresa vaze para o repositório público."""
import os
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ESTE_ARQUIVO = Path(__file__).resolve()
BASE_LOCAL = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
ARQUIVO_TERMOS = BASE_LOCAL / "DownloaderCAD" / "termos-locais"

IGNORAR_DIRETORIOS = {
    ".git", "venv", ".venv", "build", "dist", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
}
EXTENSOES = {".py", ".md", ".txt", ".json", ".spec", ".ps1", ".html", ".ini", ".toml"}
ARQUIVOS_EXTRAS = {".gitignore", "requirements.txt", "requirements-dev.txt"}


def _termos_proibidos() -> tuple[str, ...]:
    """Lista local, fora do Git: é ela que este teste precisa comparar."""
    if not ARQUIVO_TERMOS.is_file():
        return ()
    linhas = ARQUIVO_TERMOS.read_text(encoding="utf-8").splitlines()
    return tuple(termo.strip().lower() for termo in linhas if termo.strip())


def _arquivos_publicos():
    for caminho in RAIZ.rglob("*"):
        if not caminho.is_file() or caminho == ESTE_ARQUIVO:
            continue
        if any(parte in IGNORAR_DIRETORIOS for parte in caminho.parts):
            continue
        if caminho.suffix.lower() in EXTENSOES or caminho.name in ARQUIVOS_EXTRAS:
            yield caminho


def test_nenhum_termo_da_empresa_nos_arquivos_publicos():
    termos = _termos_proibidos()
    if not termos:
        pytest.skip("arquivo .termos-locais ausente")

    encontrados = []
    for caminho in _arquivos_publicos():
        try:
            texto = caminho.read_text(encoding="utf-8").lower()
        except (OSError, UnicodeDecodeError):
            continue
        for termo in termos:
            if termo in texto:
                encontrados.append(f"{caminho.relative_to(RAIZ)}: {termo}")

    assert not encontrados, "Termos da empresa encontrados:\n" + "\n".join(encontrados)


def test_exemplo_de_configuracao_nao_tem_dominio_real():
    termos = _termos_proibidos()
    if not termos:
        pytest.skip("arquivo .termos-locais ausente")

    texto = (RAIZ / "config.example.json").read_text(encoding="utf-8").lower()

    encontrados = [termo for termo in termos if termo in texto]
    assert not encontrados, f"Termos da empresa em config.example.json: {encontrados}"
