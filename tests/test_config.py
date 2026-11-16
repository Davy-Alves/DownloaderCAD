import json
from pathlib import Path

import pytest

from automacao import config


@pytest.fixture
def config_isolado(tmp_path, monkeypatch):
    """Isola os caminhos e restaura os valores do módulo ao final."""
    for chave in config.CHAVES:
        nome, _ = config.CHAVES[chave]
        monkeypatch.setattr(config, nome, getattr(config, nome))
    monkeypatch.setattr(config, "CDP_URL", config.CDP_URL)
    monkeypatch.setattr(config, "PASTA_CONFIG_USUARIO", tmp_path / "cfg")
    monkeypatch.setattr(config, "ARQUIVO_CONFIG_USUARIO", tmp_path / "cfg" / "config.json")
    monkeypatch.setattr(config, "ARQUIVO_CONFIG_EXE", tmp_path / "config-exe.json")
    return tmp_path


def test_salvar_e_ler_configuracao(config_isolado):
    config.salvar_config(
        url_portal="https://portal.exemplo.invalid/",
        perfil_login="PERFIL DE TESTE",
        porta_cdp=9333,
        limite_clientes=5,
        reprocessar_nao=True,
    )

    dados = config.ler_config()
    assert dados["url_portal"] == "https://portal.exemplo.invalid/"
    assert dados["perfil_login"] == "PERFIL DE TESTE"
    assert dados["porta_cdp"] == 9333
    assert dados["limite_clientes"] == 5
    assert dados["reprocessar_nao"] is True

    config.carregar_config()
    assert config.URL_PORTAL == "https://portal.exemplo.invalid"
    assert config.CDP_URL == "http://localhost:9333"


def test_configuracao_antiga_base_url_e_migrada(config_isolado):
    caminho = config_isolado / "cfg" / "config.json"
    caminho.parent.mkdir(parents=True)
    caminho.write_text(json.dumps({"base_url": "https://antigo.exemplo.invalid"}),
                       encoding="utf-8")

    dados = config.ler_config()

    assert dados["url_portal"] == "https://antigo.exemplo.invalid"


def test_json_invalido_levanta_erro_claro(config_isolado):
    caminho = config_isolado / "cfg" / "config.json"
    caminho.parent.mkdir(parents=True)
    caminho.write_text("{nao e json", encoding="utf-8")

    with pytest.raises(ValueError, match="configuração inválida"):
        config.ler_config()


def test_config_salvo_com_bom_de_notepad_e_lido(config_isolado):
    """Regressão: Notepad/PowerShell gravam UTF-8 com BOM e o app recusava."""
    caminho = config_isolado / "cfg" / "config.json"
    caminho.parent.mkdir(parents=True)
    caminho.write_text(
        json.dumps({"url_portal": "https://portal.exemplo.invalid"}),
        encoding="utf-8-sig",
    )

    dados = config.ler_config()

    assert dados["url_portal"] == "https://portal.exemplo.invalid"


def test_porta_e_limite_invalidos(config_isolado):
    with pytest.raises(ValueError, match="porta_cdp"):
        config.aplicar_config({"porta_cdp": 70000})
    with pytest.raises(ValueError, match="limite_clientes"):
        config.aplicar_config({"limite_clientes": 0})


def test_url_do_portal(config_isolado):
    assert config.validar_url_portal("")[0] is False
    assert config.validar_url_portal("portal.exemplo.invalid")[0] is False
    assert config.validar_url_portal("https://portal.exemplo.invalid")[0] is True
    assert config.validar_url_portal("http://portal.exemplo.invalid")[0] is True


def test_url_vazia_pode_ser_gravada(config_isolado):
    config.salvar_config(url_portal="https://portal.exemplo.invalid")
    config.salvar_config(url_portal="")

    assert config.ler_config()["url_portal"] == ""
    assert Path(config.ARQUIVO_CONFIG_USUARIO).exists()
