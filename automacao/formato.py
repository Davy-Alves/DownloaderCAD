"""Validação do formato da planilha e geração do modelo de exemplo."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from automacao.planilha import Planilha

COLUNAS_OBRIGATORIAS = ("SOLICITACAO", "Nome do cliente", "CAD")
COLUNAS_OPCIONAIS = ("MUNICIPIO",)
NOME_MODELO = "modelo_planilha.xlsx"


@dataclass
class ResultadoValidacao:
    """Resultado da checagem feita antes de iniciar."""
    ok: bool
    mensagem: str
    pendentes: int = 0
    ja_preenchidas: int = 0
    avisos: list[str] = field(default_factory=list)


def texto_formato() -> str:
    """Texto em linguagem simples para o botão 'Ver formato aceito'."""
    return "\n".join([
        "FORMATO ACEITO PELO DOWNLOADER CAD",
        "",
        "Arquivo: .xlsx (Excel), primeira aba.",
        "Cabeçalho: em qualquer uma das 20 primeiras linhas.",
        "",
        "Colunas obrigatórias:",
        "  - SOLICITACAO",
        "  - Nome do cliente",
        "  - CAD",
        "",
        "Coluna opcional:",
        "  - MUNICIPIO (usada para filtrar a consulta no portal)",
        "",
        "Regras:",
        "  - A coluna CAD deve começar vazia; o robô grava SIM ou NÃO.",
        "  - Linhas com CAD já preenchido são puladas.",
        "  - Se a consulta falhar, a célula fica em branco para a próxima rodada.",
        "  - Feche a planilha no Excel antes de iniciar.",
        "  - Cada linha precisa ter SOLICITACAO e Nome do cliente preenchidos.",
        "  - A pasta de destino precisa existir; o programa não cria a pasta raiz.",
        "",
        "Exemplo (cabeçalho na linha 2):",
        "",
        "  SOLICITACAO | Nome do cliente    | MUNICIPIO        | CAD",
        "  12345678    | CLIENTE EXEMPLO 1  | MUNICIPIO EXEMPLO|",
        "  87654321    | CLIENTE EXEMPLO 2  | OUTRO MUNICIPIO  |",
        "",
        "Use o botão 'Baixar modelo' para gerar um arquivo pronto.",
    ])


def validar_destino(pasta) -> tuple[bool, str]:
    """Confere se a pasta de destino existe. Nunca cria a pasta."""
    if not pasta:
        return False, "Escolha a pasta de destino dos DWG."
    caminho = Path(pasta)
    if not caminho.is_dir():
        return False, f"A pasta de destino não existe: {caminho}"
    return True, "Pasta de destino OK."


def validar_planilha(caminho) -> ResultadoValidacao:
    """Confere o formato e conta as linhas pendentes, sem alterar o arquivo."""
    if not caminho:
        return ResultadoValidacao(False, "Escolha a planilha de controle (.xlsx).")

    caminho = Path(caminho)
    if not caminho.is_file():
        return ResultadoValidacao(False, f"Arquivo não encontrado: {caminho}")
    if caminho.suffix.lower() != ".xlsx":
        return ResultadoValidacao(False, "O arquivo precisa ser .xlsx (Excel).")

    avisos = []
    trava = caminho.with_name(f"~${caminho.name}")
    if trava.exists():
        avisos.append(
            "A planilha parece estar aberta no Excel. Feche o arquivo antes de iniciar; "
            "enquanto ele estiver aberto, o robô não consegue salvar."
        )

    try:
        planilha = Planilha(caminho)
    except ValueError as erro:
        return ResultadoValidacao(False, str(erro))
    except Exception as erro:
        return ResultadoValidacao(False, f"Não consegui abrir a planilha: {erro}")

    try:
        df = planilha.carregar_dataframe()
    except Exception as erro:
        return ResultadoValidacao(False, f"Não consegui ler a planilha: {erro}")

    faltando = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in df.columns]
    if faltando:
        return ResultadoValidacao(
            False, "Faltam colunas obrigatórias: " + ", ".join(faltando) + "."
        )

    try:
        pendentes, ja_preenchidas = planilha.carregar_pendentes(df=df)
    except Exception as erro:
        return ResultadoValidacao(False, f"Não consegui contar as linhas: {erro}")
    quantidade_pendentes = len(pendentes)

    # Bug conhecido: com células vazias, o pandas lê SOLICITACAO como float e
    # o nome da pasta pode sair como "222.0". Avisa, mas não corrige sozinho
    # (corrigir mudaria o nome das pastas já baixadas).
    if df["SOLICITACAO"].dtype.kind == "f":
        avisos.append(
            "A coluna SOLICITACAO tem células vazias e foi lida como número decimal. "
            "O nome das pastas pode sair como 222.0. Preencha a coluna para evitar isso."
        )

    if not quantidade_pendentes and not ja_preenchidas:
        return ResultadoValidacao(
            False,
            "Não encontrei nenhuma linha com SOLICITACAO e Nome do cliente preenchidos.",
            0, 0, avisos,
        )
    if not quantidade_pendentes:
        return ResultadoValidacao(
            True,
            f"Planilha OK. Todas as {ja_preenchidas} linha(s) já estão com CAD preenchido; "
            "não há nada a fazer.",
            0, ja_preenchidas, avisos,
        )
    return ResultadoValidacao(
        True,
        f"Planilha OK: {quantidade_pendentes} linha(s) pendente(s) e "
        f"{ja_preenchidas} já preenchida(s).",
        quantidade_pendentes, ja_preenchidas, avisos,
    )


def gerar_modelo(destino) -> Path:
    """Gera um .xlsx de exemplo com dados fictícios."""
    destino = Path(destino)
    if destino.suffix.lower() != ".xlsx":
        destino = destino.with_suffix(".xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "Controle"
    ws.append(["Modelo de planilha - Downloader CAD"])
    ws.append(["SOLICITACAO", "Nome do cliente", "MUNICIPIO", "CAD"])
    ws.append([12345678, "CLIENTE EXEMPLO 1", "MUNICIPIO EXEMPLO", None])
    ws.append([87654321, "CLIENTE EXEMPLO 2", "OUTRO MUNICIPIO", None])

    cabecalho = ws[2]
    for celula in cabecalho:
        celula.font = Font(bold=True)
        celula.fill = PatternFill("solid", fgColor="D9EAD3")
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 10

    instrucoes = wb.create_sheet("Instruções")
    for numero, linha in enumerate(texto_formato().splitlines(), start=1):
        instrucoes.cell(row=numero, column=1, value=linha)
    instrucoes.column_dimensions["A"].width = 90

    wb.save(destino)
    return destino
