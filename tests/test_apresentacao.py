from automacao import apresentacao


def test_botoes_no_estado_ocioso():
    botoes = apresentacao.botoes_habilitados("ocioso", True, True)

    assert botoes["carregar"] and botoes["pasta"] and botoes["iniciar"]
    assert not botoes["login"] and not botoes["parar"] and not botoes["finalizar"]


def test_botoes_sem_planilha_ou_destino_nao_iniciam():
    assert not apresentacao.botoes_habilitados("ocioso", False, True)["iniciar"]
    assert not apresentacao.botoes_habilitados("ocioso", True, False)["iniciar"]


def test_botoes_durante_a_execucao():
    botoes = apresentacao.botoes_habilitados("executando", True, True)

    assert not botoes["carregar"] and not botoes["iniciar"]
    assert botoes["pausar"] and botoes["parar"] and botoes["finalizar"]
    assert not botoes["retomar"]


def test_botoes_de_login_e_retomada():
    login = apresentacao.botoes_habilitados("aguardando_login", True, True)
    pausado = apresentacao.botoes_habilitados("pausado", True, True)

    assert login["login"] and not login["iniciar"]
    assert pausado["retomar"] and not pausado["pausar"]


def test_todos_os_estados_tem_rotulo():
    estados = [
        "ocioso", "abrindo", "aguardando_login", "executando",
        "pausado", "sessao_caiu", "finalizado", "parado", "erro",
    ]
    assert set(estados) == set(apresentacao.ROTULOS_ESTADO)


# --- Padrão visual: níveis de botão e estados -------------------------------

PRIMARIO_ESPERADO = {
    "ocioso": {"iniciar"},
    "abrindo": set(),
    "aguardando_login": {"login"},
    "executando": set(),
    "pausado": {"retomar"},
    "sessao_caiu": {"iniciar"},
    "finalizado": {"finalizar"},
    "parado": {"finalizar"},
    "erro": {"iniciar"},
}


def test_no_maximo_um_botao_primario_por_estado():
    for estado, esperado in PRIMARIO_ESPERADO.items():
        niveis = apresentacao.niveis_dos_botoes(estado)
        primarios = {nome for nome, nivel in niveis.items() if nivel == "primario"}

        assert primarios == esperado, estado


def test_parar_e_finalizar_sao_perigo():
    for estado in apresentacao.ROTULOS_ESTADO:
        niveis = apresentacao.niveis_dos_botoes(estado)

        assert niveis["parar"] == "perigo"
        if estado in apresentacao.ESTADOS_AGUARDANDO_FINALIZAR:
            assert niveis["finalizar"] == "primario"
        else:
            assert niveis["finalizar"] == "perigo"


def test_niveis_cobrem_todos_os_botoes_da_tela():
    niveis = apresentacao.niveis_dos_botoes("ocioso")

    assert set(niveis) == {
        "carregar", "pasta", "config", "iniciar", "login",
        "pausar", "retomar", "parar", "finalizar",
    }


def test_iniciar_so_libera_depois_de_finalizar():
    """Com a rodada terminada, o caminho é Finalizar -> nova rodada."""
    for estado in apresentacao.ESTADOS_AGUARDANDO_FINALIZAR:
        botoes = apresentacao.botoes_habilitados(estado, True, True)

        assert botoes["iniciar"] is False
        assert botoes["finalizar"] is True


def test_iniciar_continua_disponivel_quando_a_sessao_caiu():
    for estado in ("sessao_caiu", "erro"):
        botoes = apresentacao.botoes_habilitados(estado, True, True)

        assert botoes["iniciar"] is True
        assert botoes["finalizar"] is True


def test_configuracoes_desabilitadas_durante_a_execucao():
    for estado in apresentacao.ESTADOS_EM_EXECUCAO:
        assert apresentacao.botoes_habilitados(estado, True, True)["config"] is False

    assert apresentacao.botoes_habilitados("ocioso", True, True)["config"] is True


def test_janela_cabe_na_area_util_da_tela():
    """Regressão: em 1080p a 125% a janela passava da barra de tarefas."""
    assert apresentacao.altura_da_janela(864) == 744
    assert apresentacao.altura_da_janela(1080) == apresentacao.ALTURA_JANELA
    assert apresentacao.altura_da_janela(768) == 648
    assert apresentacao.altura_da_janela(600) == apresentacao.ALTURA_MINIMA_JANELA


def test_paleta_tem_os_tres_niveis_e_o_desabilitado():
    for nivel in ("primario", "secundario", "perigo", "desabilitado"):
        cores = apresentacao.PALETA[nivel]
        for chave in ("fundo", "texto", "borda", "hover", "pressionado", "foco"):
            assert cores[chave].startswith("#"), (nivel, chave)


# --- Painel "Analisando agora" ----------------------------------------------

def test_painel_mostra_cliente_ordem_solicitacao_e_linha():
    foco, detalhe = apresentacao.painel_em_analise(
        "executando", cliente="CLIENTE EXEMPLO", ordem=222,
        solicitacao="1001", linha=39,
    )

    assert foco == "Cliente: CLIENTE EXEMPLO"
    assert detalhe == "Ordem 222 · Solicitação 1001 · linha 39 da planilha"


def test_painel_sem_solicitacao_ainda_mostra_cliente_e_ordem():
    foco, detalhe = apresentacao.painel_em_analise(
        "executando", cliente="CLIENTE EXEMPLO", ordem=222, linha=3,
    )

    assert foco == "Cliente: CLIENTE EXEMPLO"
    assert detalhe == "Ordem 222 · linha 3 da planilha"


def test_painel_sem_cliente_explica_o_estado():
    assert apresentacao.painel_em_analise("pausado") == (
        "Execução pausada", "Clique em Retomar para continuar."
    )
    foco, dica = apresentacao.painel_em_analise("aguardando_login")
    assert "Já estou logado" in dica
    assert apresentacao.painel_em_analise("finalizado", mensagem="Tudo certo") == (
        "Rodada finalizada", "Tudo certo"
    )


# --- Formatação das linhas do log -------------------------------------------

def test_log_info_nao_mostra_o_rotulo():
    linha, tag = apresentacao.formatar_linha_log("09:12:44", "INFO", "Solicitação 1001: baixando a.dwg...")

    assert linha == "09:12:44  Solicitação 1001: baixando a.dwg...\n"
    assert tag == "INFO"


def test_log_aviso_e_erro_continuam_identificados():
    aviso, tag_aviso = apresentacao.formatar_linha_log("09:13:00", "AVISO", "Pausando...")
    erro, tag_erro = apresentacao.formatar_linha_log("09:14:00", "ERRO", "Falhou")

    assert aviso == "09:13:00  AVISO Pausando...\n"
    assert tag_aviso == "AVISO"
    assert erro == "09:14:00  ERRO  Falhou\n"
    assert tag_erro == "ERRO"


def test_log_linha_do_cliente_em_destaque_e_separada():
    linha, tag = apresentacao.formatar_linha_log(
        "09:12:44", "INFO", "» Cliente 1 de 2: CLIENTE EXEMPLO — Ordem 222 (linha 3 da planilha)"
    )

    assert linha.startswith("\n09:12:44  » Cliente 1 de 2")
    assert tag == "DESTAQUE"


def test_listar_solicitacoes_usa_linguagem_simples():
    assert apresentacao.listar_solicitacoes(["1001"]) == "1001"
    assert apresentacao.listar_solicitacoes(["1001", "1002"]) == "1001 e 1002"
    assert apresentacao.listar_solicitacoes(["1001", "1002", "1003"]) == "1001, 1002 e 1003"
    assert apresentacao.listar_solicitacoes([]) == ""
