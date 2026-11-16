import logging

import pytest

from automacao import registro
from automacao.controle import Controle
from automacao.resumo import Resumo


@pytest.fixture
def logger_temporario(tmp_path):
    logger = registro.configurar(Controle(Resumo(), espera=0.01), tmp_path)
    yield logger, tmp_path
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_log_vai_para_arquivo_e_para_a_janela(logger_temporario):
    logger, pasta = logger_temporario
    logger.info("mensagem de teste")
    logger.warning("aviso de teste")

    arquivo = (pasta / "downloadercad.log").read_text(encoding="utf-8")
    assert "mensagem de teste" in arquivo
    assert "[WARNING] aviso de teste" in arquivo


def test_fluxo_log_quebra_linhas_e_repassa_para_o_logger(logger_temporario):
    logger, pasta = logger_temporario
    fluxo = registro.FluxoLog(logger)
    fluxo.write("linha um\nlinha dois\n")

    arquivo = (pasta / "downloadercad.log").read_text(encoding="utf-8")
    assert "linha um" in arquivo
    assert "linha dois" in arquivo
    assert logging.getLogger("downloadercad") is logger
