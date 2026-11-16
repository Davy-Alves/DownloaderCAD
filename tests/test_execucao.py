from pathlib import Path

import pytest

from automacao.controle import Controle
from automacao.execucao import Preparacao, _finalizar, executar, preparar
from automacao.resumo import Resumo


class PlanilhaFake:
    def __init__(self):
        self.salvo = False

    def salvar(self):
        self.salvo = True


def _preparacao(planilha, pendentes=(), ja=0):
    return Preparacao(
        planilha=planilha,
        pendentes=list(pendentes),
        ja_preenchidas=ja,
        caminho_excel=Path("planilha.xlsx"),
        pasta_downloads=Path("destino"),
    )


def test_finalizar_nao_salva_planilha_sem_marcacao():
    planilha = PlanilhaFake()
    controle = Controle(Resumo())
    resultado = _finalizar(controle, Resumo(), _preparacao(planilha), "finalizado", "ok")

    assert resultado.estado == "finalizado"
    assert planilha.salvo is False


def test_finalizar_salva_planilha_quando_ouve_marcacao():
    planilha = PlanilhaFake()
    controle = Controle(Resumo())
    controle.set(com_cad=1)
    _finalizar(controle, Resumo(), _preparacao(planilha), "finalizado", "ok")

    assert planilha.salvo is True


def test_executar_sem_pendentes_nao_abre_chrome():
    planilha = PlanilhaFake()
    controle = Controle(Resumo())
    resumo = Resumo()

    resultado = executar(_preparacao(planilha), controle, resumo)

    assert resultado.estado == "finalizado"
    assert planilha.salvo is False
    assert controle.get("estado") == "finalizado"


def test_preparar_exige_planilha_e_pasta():
    with pytest.raises(ValueError, match="planilha"):
        preparar(None, Path("destino"))
    with pytest.raises(ValueError, match="pasta"):
        preparar(Path("planilha.xlsx"), None)
