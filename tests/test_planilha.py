import pytest
from openpyxl import Workbook, load_workbook

from automacao.planilha import Planilha


def test_pendentes_sao_so_as_linhas_com_cad_vazio(criar_planilha):
    caminho = criar_planilha([
        (111, "ANA", "FORTALEZA", "SIM"),   # linha 3: já marcada
        (222, "BRUNO", "SOBRAL", None),     # linha 4: pendente
        (None, "SEM ORDEM", "X", None),     # linha 5: sem ordem, ignorada
        (333, "CARLA", "CRATO", "NÃO"),     # linha 6: já marcada
        (444, "DIEGO", "IGUATU", None),     # linha 7: pendente
    ])
    pendentes, ja = Planilha(caminho).carregar_pendentes()

    assert ja == 2
    assert [(p.linha_excel, p.cliente) for p in pendentes] == [(4, "BRUNO"), (7, "DIEGO")]


def test_reprocessar_nao_inclui_as_marcadas_com_nao_mas_nunca_as_com_sim(criar_planilha):
    caminho = criar_planilha([
        (111, "ANA", "X", "SIM"),
        (222, "BRUNO", "X", "NÃO"),
    ])
    pendentes, ja = Planilha(caminho).carregar_pendentes(reprocessar_nao=True)

    assert [p.cliente for p in pendentes] == ["BRUNO"]
    assert ja == 1


def test_gravar_cad_salva_no_arquivo_e_preserva_as_outras_colunas(criar_planilha, ler_cad):
    caminho = criar_planilha([(222, "BRUNO", "SOBRAL", None)])
    Planilha(caminho).gravar_cad(3, "SIM")

    assert ler_cad(caminho, 3) == "SIM"
    ws = load_workbook(caminho).worksheets[0]
    assert [ws.cell(row=3, column=c).value for c in (1, 2, 3)] == [222, "BRUNO", "SOBRAL"]


def test_planilha_sem_coluna_cad_levanta_erro_claro(tmp_path):
    caminho = tmp_path / "sem_cad.xlsx"
    wb = Workbook()
    wb.active.append(["SOLICITACAO", "Nome do cliente"])
    wb.save(caminho)

    with pytest.raises(ValueError, match="CAD"):
        Planilha(caminho)


def test_excel_aberto_nao_derruba_o_script(criar_planilha, monkeypatch, capsys):
    """Regressão: com o Excel aberto o save falha; deve avisar e seguir, não quebrar."""
    planilha = Planilha(criar_planilha([(222, "BRUNO", "SOBRAL", None)]))

    def salvar_bloqueado(_):
        raise PermissionError

    monkeypatch.setattr(planilha.wb, "save", salvar_bloqueado)

    assert planilha.salvar() is False
    assert "Excel" in capsys.readouterr().out


@pytest.mark.xfail(reason="BUG CONHECIDO: ordem vira '222.0' quando há célula vazia na coluna (pandas lê como float)",
                   strict=True)
def test_ordem_nao_vira_decimal(criar_planilha):
    caminho = criar_planilha([(222, "BRUNO", "X", None), (None, "SEM ORDEM", "X", None)])
    pendentes, _ = Planilha(caminho).carregar_pendentes()

    assert pendentes[0].ordem == "222"
