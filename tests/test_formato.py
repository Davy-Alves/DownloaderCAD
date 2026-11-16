import pytest
from openpyxl import Workbook, load_workbook

from automacao.formato import (
    COLUNAS_OBRIGATORIAS,
    gerar_modelo,
    texto_formato,
    validar_destino,
    validar_planilha,
)
from automacao.execucao import preparar


def _planilha(tmp_path, cabecalho, linhas=(), nome="base.xlsx"):
    caminho = tmp_path / nome
    wb = Workbook()
    ws = wb.active
    ws.append(["Título"])
    ws.append(cabecalho)
    for linha in linhas:
        ws.append(list(linha))
    wb.save(caminho)
    return caminho


def test_planilha_valida_conta_pendentes(criar_planilha):
    caminho = criar_planilha([
        (111, "ANA", "X", "SIM"),
        (222, "BRUNO", "X", None),
    ])
    resultado = validar_planilha(caminho)

    assert resultado.ok
    assert resultado.pendentes == 1
    assert resultado.ja_preenchidas == 1


def test_sem_coluna_cad_erro_claro(tmp_path):
    caminho = _planilha(tmp_path, ["SOLICITACAO", "Nome do cliente"], [(1, "ANA")])
    resultado = validar_planilha(caminho)

    assert not resultado.ok
    assert "CAD" in resultado.mensagem


def test_sem_coluna_solicitacao_erro_claro(tmp_path):
    caminho = _planilha(tmp_path, ["Nome do cliente", "CAD"], [("ANA", None)])
    resultado = validar_planilha(caminho)

    assert not resultado.ok
    assert "SOLICITACAO" in resultado.mensagem


def test_preparar_recusa_planilha_sem_colunas_obrigatorias(tmp_path):
    caminho = _planilha(tmp_path, ["Nome do cliente", "CAD"], [("ANA", None)])

    with pytest.raises(ValueError, match="SOLICITACAO"):
        preparar(caminho, tmp_path)


def test_extensao_errada(tmp_path):
    caminho = tmp_path / "base.csv"
    caminho.write_text("x", encoding="utf-8")
    resultado = validar_planilha(caminho)

    assert not resultado.ok
    assert ".xlsx" in resultado.mensagem


def test_arquivo_inexistente(tmp_path):
    resultado = validar_planilha(tmp_path / "nao_existe.xlsx")

    assert not resultado.ok


def test_avisa_excel_aberto(tmp_path, criar_planilha):
    caminho = criar_planilha([(222, "BRUNO", "X", None)])
    (tmp_path / f"~${caminho.name}").write_text("", encoding="utf-8")

    resultado = validar_planilha(caminho)

    assert resultado.ok
    assert any("Excel" in aviso for aviso in resultado.avisos)


def test_avisa_solicitacao_com_celula_vazia(tmp_path):
    caminho = _planilha(
        tmp_path,
        ["SOLICITACAO", "Nome do cliente", "MUNICIPIO", "CAD"],
        [(222, "BRUNO", "X", None), (None, "SEM ORDEM", "X", None)],
    )
    resultado = validar_planilha(caminho)

    assert resultado.ok
    assert any("222.0" in aviso for aviso in resultado.avisos)


def test_destino_precisa_existir(tmp_path):
    ok, mensagem = validar_destino(tmp_path / "nao_existe")
    assert not ok
    assert "não existe" in mensagem

    ok, _ = validar_destino(tmp_path)
    assert ok

    ok, _ = validar_destino(None)
    assert not ok


def test_modelo_tem_as_colunas_e_dados_ficticios(tmp_path):
    destino = gerar_modelo(tmp_path / "modelo.xlsx")
    wb = load_workbook(destino)
    ws = wb.worksheets[0]

    assert [ws.cell(row=2, column=c).value for c in range(1, 5)] == [
        "SOLICITACAO", "Nome do cliente", "MUNICIPIO", "CAD"
    ]
    assert ws.cell(row=3, column=2).value == "CLIENTE EXEMPLO 1"
    assert ws.cell(row=3, column=4).value is None
    assert wb.sheetnames == ["Controle", "Instruções"]


def test_texto_formato_cita_as_colunas():
    texto = texto_formato()

    for coluna in COLUNAS_OBRIGATORIAS:
        assert coluna in texto
