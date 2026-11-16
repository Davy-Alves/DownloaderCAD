"""Regras de apresentação puras (sem Tkinter), para poder testar."""
from __future__ import annotations

ROTULOS_ESTADO = {
    "ocioso": "Pronto para começar",
    "abrindo": "Abrindo o Chrome...",
    "aguardando_login": "Aguardando login",
    "executando": "Executando",
    "pausado": "Pausado",
    "sessao_caiu": "Sessão caiu",
    "finalizado": "Finalizado",
    "parado": "Interrompido",
    "erro": "Erro",
}

CORES_ESTADO = {
    "ocioso": "#374151",
    "abrindo": "#1d4ed8",
    "aguardando_login": "#b45309",
    "executando": "#15803d",
    "pausado": "#b45309",
    "sessao_caiu": "#b91c1c",
    "finalizado": "#15803d",
    "parado": "#b45309",
    "erro": "#b91c1c",
}

ESTADOS_EM_EXECUCAO = {"abrindo", "aguardando_login", "executando", "pausado"}
ESTADOS_ENCERRADOS = {"finalizado", "parado", "sessao_caiu", "erro"}

# Altura da janela em pixels de 96 dpi e a folga reservada para a barra de
# título e a barra de tarefas. Sem esse limite o rodapé do log fica atrás da
# barra de tarefas em telas de 1080p com escala de 125%.
ALTURA_JANELA = 760
MARGEM_VERTICAL = 120
ALTURA_MINIMA_JANELA = 640

# A rodada terminou, mas ainda não foi "Finalizar": a próxima ação é encerrar
# para liberar a próxima. Se Iniciar ficasse habilitado aqui, haveria dois
# caminhos na mesma tela e o botão Finalizar perderia o sentido.
ESTADOS_AGUARDANDO_FINALIZAR = {"finalizado", "parado"}

# Três níveis: primário (a ação do momento), secundário (ações normais) e
# perigo (encerra a execução). `desabilitado` não é nível de botão: é a
# aparência aplicada quando ele não pode ser clicado.
PALETA = {
    "primario": {
        "fundo": "#1d4ed8",
        "texto": "#ffffff",
        "borda": "#1d4ed8",
        "hover": "#1e40af",
        "pressionado": "#1e3a8a",
        "foco": "#1e3a8a",
    },
    "secundario": {
        "fundo": "#ffffff",
        "texto": "#374151",
        "borda": "#d1d5db",
        "hover": "#f3f4f6",
        "pressionado": "#e5e7eb",
        "foco": "#6b7280",
    },
    "perigo": {
        "fundo": "#ffffff",
        "texto": "#b91c1c",
        "borda": "#fecaca",
        "hover": "#fee2e2",
        "pressionado": "#fecaca",
        "foco": "#b91c1c",
    },
    "desabilitado": {
        "fundo": "#f3f4f6",
        "texto": "#9ca3af",
        "borda": "#e5e7eb",
        "hover": "#f3f4f6",
        "pressionado": "#f3f4f6",
        "foco": "#e5e7eb",
    },
}


# --- Painel "Analisando agora" e log ---------------------------------------
# O print() do robô chega ao log como INFO. O marcador é o que permite ao
# render saber que aquela linha merece negrito (cliente em análise) sem
# precisar de outro canal de log.
MARCA_DESTAQUE = "» "


def listar_solicitacoes(numeros) -> str:
    """Lista em linguagem simples: '1001' ou '1001 e 1002'."""
    numeros = [str(numero) for numero in numeros]
    if not numeros:
        return ""
    if len(numeros) == 1:
        return numeros[0]
    return ", ".join(numeros[:-1]) + " e " + numeros[-1]


def painel_em_analise(
    estado: str,
    cliente: str = "",
    ordem=None,
    solicitacao="",
    linha=None,
    mensagem: str = "",
) -> tuple[str, str]:
    """Linha de destaque e linha de detalhe do painel 'Analisando agora'.

    O cliente vem em destaque; ordem, solicitação e linha da planilha vêm na
    linha de baixo, do jeito que o usuário lê a planilha.
    """
    if cliente:
        partes = []
        if ordem not in (None, ""):
            partes.append(f"Ordem {ordem}")
        if solicitacao not in (None, ""):
            partes.append(f"Solicitação {solicitacao}")
        if linha not in (None, ""):
            partes.append(f"linha {linha} da planilha")
        return f"Cliente: {cliente}", " · ".join(partes)

    if estado == "aguardando_login":
        return (
            "Aguardando você entrar no portal",
            'Faça login no Chrome e clique em "Já estou logado".',
        )
    if estado == "pausado":
        return "Execução pausada", "Clique em Retomar para continuar."
    if estado == "abrindo":
        return "Abrindo o Chrome…", "O portal abre em instantes."
    if estado == "executando":
        return "Preparando o próximo cliente…", ""
    if estado == "finalizado":
        return "Rodada finalizada", mensagem or "Confira o resultado na planilha."
    if estado == "parado":
        return "Execução interrompida", mensagem or "O progresso já foi salvo na planilha."
    if estado == "sessao_caiu":
        return (
            "Sessão do portal caiu",
            mensagem or "Faça login de novo e clique em Iniciar para continuar.",
        )
    if estado == "erro":
        return "A execução parou com erro", mensagem
    return "Aguardando o início", 'Escolha a planilha e clique em "Iniciar".'


def formatar_linha_log(hora: str, nivel: str, texto: str) -> tuple[str, str]:
    """Monta uma linha do painel de log e devolve (linha, tag de cor).

    INFO não repete o rótulo: o usuário leigo não precisa saber o que é INFO.
    Só OK, AVISO e ERRO aparecem, porque são os que pedem atenção. A linha do
    cliente chega como INFO com MARCA_DESTAQUE e sai em negrito, separada por
    uma linha em branco.
    """
    texto = str(texto)
    if nivel == "INFO":
        if texto.startswith(MARCA_DESTAQUE):
            return f"\n{hora}  {texto}\n", "DESTAQUE"
        return f"{hora}  {texto}\n", "INFO"
    if nivel not in ("OK", "AVISO", "ERRO"):
        nivel = "INFO"
    return f"{hora}  {nivel:<5} {texto}\n", nivel


def altura_da_janela(altura_tela: int) -> int:
    """Altura que cabe na tela descontando título e barra de tarefas."""
    return max(ALTURA_MINIMA_JANELA, min(ALTURA_JANELA, altura_tela - MARGEM_VERTICAL))


def botoes_habilitados(estado: str, tem_planilha: bool, tem_destino: bool) -> dict:
    """Quais botões ficam clicáveis em cada estado."""
    em_execucao = estado in ESTADOS_EM_EXECUCAO
    aguardando_finalizar = estado in ESTADOS_AGUARDANDO_FINALIZAR
    return {
        "carregar": not em_execucao,
        "pasta": not em_execucao,
        "config": not em_execucao,
        "iniciar": (
            not em_execucao and not aguardando_finalizar
            and tem_planilha and tem_destino
        ),
        "login": estado == "aguardando_login",
        "pausar": estado == "executando",
        "retomar": estado == "pausado",
        "parar": em_execucao,
        "finalizar": estado != "ocioso",
    }


def niveis_dos_botoes(estado: str) -> dict:
    """Nível visual de cada botão, com no máximo um destaque por estado.

    - `ocioso` / `sessao_caiu` / `erro`: Iniciar é a próxima ação.
    - `aguardando_login`: o destaque passa para "Já estou logado".
    - `pausado`: o destaque passa para Retomar.
    - `executando` / `abrindo`: nada a fazer além de esperar, então nenhum
      botão fica primário.
    - `finalizado` / `parado`: Finalizar é a próxima ação e deixa de ser perigo.
    """
    niveis = {nome: "secundario" for nome in (
        "carregar", "pasta", "config", "iniciar", "login",
        "pausar", "retomar", "parar", "finalizar",
    )}
    niveis["parar"] = "perigo"
    niveis["finalizar"] = "perigo"

    if estado in ESTADOS_AGUARDANDO_FINALIZAR:
        niveis["finalizar"] = "primario"
    elif estado == "pausado":
        niveis["retomar"] = "primario"
    elif estado == "aguardando_login":
        niveis["login"] = "primario"
    elif estado not in ("abrindo", "executando"):
        niveis["iniciar"] = "primario"
    return niveis


def esta_em_execucao(estado: str) -> bool:
    return estado in ESTADOS_EM_EXECUCAO


def esta_encerrado(estado: str) -> bool:
    return estado in ESTADOS_ENCERRADOS
