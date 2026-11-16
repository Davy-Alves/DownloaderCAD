import csv
import threading
import time

import pytest

from automacao.controle import Controle
from automacao.excecoes import Interrompido
from automacao.resumo import Resumo


@pytest.fixture
def controle(tmp_path):
    return Controle(Resumo(), historico_path=tmp_path / "alteracoes.csv", espera=0.01)


def test_snapshot_reflete_estado_e_resumo(controle):
    controle._resumo.sucesso.append("x")
    controle.set(total_geral=120, concluidos=35, cliente_atual="Cliente X")
    status = controle.snapshot()

    assert (status["total_geral"], status["concluidos"], status["baixados"]) == (120, 35, 1)


def test_log_guarda_hora_nivel_e_sequencia(controle):
    controle.registrar_log("INFO", "primeira")
    controle.registrar_log("WARNING", "segunda")
    log = controle.snapshot()["log"]

    assert [item["texto"] for item in log] == ["primeira", "segunda"]
    assert log[1]["nivel"] == "AVISO"
    assert log[0]["seq"] < log[1]["seq"]
    assert len(log[0]["hora"]) == 8


def test_historico_csv_registra_alteracao(controle, tmp_path):
    controle.registrar_alteracao(42, "CLIENTE EXEMPLO", "222", "1001", "SIM")

    with (tmp_path / "alteracoes.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.reader(arquivo, delimiter=";"))

    assert linhas[0] == [
        "data_hora", "linha", "cliente", "ordem", "solicitacao", "resultado", "detalhe",
    ]
    assert linhas[1][1:6] == ["42", "CLIENTE EXEMPLO", "222", "1001", "SIM"]
    assert "CAD = SIM" in controle.snapshot()["log"][-1]["texto"]
    assert "Solicitação 1001" in controle.snapshot()["log"][-1]["texto"]


def test_snapshot_expoe_ordem_e_solicitacao_atuais(controle):
    controle.set(ordem_atual="222", solicitacao_atual="1001")

    status = controle.snapshot()

    assert status["ordem_atual"] == "222"
    assert status["solicitacao_atual"] == "1001"


def test_reiniciar_limpa_ordem_e_solicitacao(controle):
    controle.set(ordem_atual="222", solicitacao_atual="1001")

    controle.reiniciar()

    assert controle.get("ordem_atual") is None
    assert controle.get("solicitacao_atual") == ""


def test_pausa_espera_o_retomar(controle):
    controle.evt_pausar.set()
    threading.Timer(0.15, controle.evt_pausar.clear).start()
    inicio = time.time()
    controle.aguardar_se_pausado()

    assert time.time() - inicio >= 0.10
    assert controle.get("estado") == "executando"


def test_parar_libera_a_espera_pelo_inicio(controle):
    controle.evt_parar.set()

    with pytest.raises(Interrompido):
        controle.aguardar_inicio()


def test_parar_libera_a_pausa(controle):
    controle.evt_pausar.set()
    controle.evt_parar.set()

    with pytest.raises(Interrompido):
        controle.aguardar_se_pausado()

    assert not controle.evt_pausar.is_set()


def test_reiniciar_limpa_estado_mas_mantem_log(controle):
    controle.set(estado="finalizado", concluidos=10, com_cad=2)
    controle.registrar_log("INFO", "algo aconteceu")
    controle.evt_parar.set()

    controle.reiniciar()

    assert controle.get("estado") == "ocioso"
    assert controle.get("concluidos") == 0
    assert controle.get("com_cad") == 0
    assert not controle.evt_parar.is_set()
    assert controle.snapshot()["log"][-1]["texto"] == "algo aconteceu"
