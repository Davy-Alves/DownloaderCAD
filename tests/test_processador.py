import pytest

from automacao import config
from automacao.excecoes import Interrompido, SessaoExpirada
from automacao.processador import processar_clientes
from tests.fakes import SiteFake


def rodar(c):
    processar_clientes(c["pendentes"], c["planilha"], c["contexto"], c["pagina"], c["controle"], c["resumo"])


def test_baixa_o_ultimo_dwg_e_marca_sim(cenario, ler_cad):
    site = SiteFake(solicitacoes={"BRUNO": ["1001"]}, dwgs={"1001": ["antigo.dwg", "recente.dwg"]})
    c = cenario([(222, "BRUNO", "SOBRAL", None)], site)
    rodar(c)

    pasta = config.PASTA_DOWNLOADS / "BRUNO" / c["pendentes"][0].ordem / "1001"
    assert (pasta / "recente.dwg").exists()
    assert not (pasta / "antigo.dwg").exists()
    assert ler_cad(c["caminho"], 3) == "SIM"
    assert c["resumo"].sucesso == ["BRUNO (1001)"]


def test_usa_pasta_de_destino_recebida(cenario, tmp_path):
    site = SiteFake(solicitacoes={"BRUNO": ["1001"]}, dwgs={"1001": ["recente.dwg"]})
    c = cenario([(222, "BRUNO", "SOBRAL", None)], site)
    destino = tmp_path / "destino-escolhido"
    destino.mkdir()

    processar_clientes(
        c["pendentes"], c["planilha"], c["contexto"], c["pagina"],
        c["controle"], c["resumo"], pasta_downloads=destino,
    )

    assert (destino / "BRUNO" / c["pendentes"][0].ordem / "1001" / "recente.dwg").exists()


def test_cliente_sem_solicitacao_marca_nao(cenario, ler_cad):
    c = cenario([(222, "CARLA", "CRATO", None)], SiteFake())
    rodar(c)

    assert ler_cad(c["caminho"], 3) == "NÃO"


def test_solicitacao_sem_dwg_marca_nao(cenario, ler_cad):
    site = SiteFake(solicitacoes={"DIEGO": ["1002"]}, dwgs={"1002": []})
    c = cenario([(222, "DIEGO", "IGUATU", None)], site)
    rodar(c)

    assert ler_cad(c["caminho"], 3) == "NÃO"


def test_dwg_ja_baixado_e_pulado_e_marca_sim(cenario, ler_cad):
    site = SiteFake(solicitacoes={"ELISA": ["1003"]})
    c = cenario([(222, "ELISA", "CRATEUS", None)], site)
    pasta = config.PASTA_DOWNLOADS / "ELISA" / c["pendentes"][0].ordem / "1003"
    pasta.mkdir(parents=True)
    (pasta / "ja_existe.dwg").write_bytes(b"x")
    rodar(c)

    assert c["resumo"].pulados == ["ELISA (1003)"]
    assert c["resumo"].sucesso == []
    assert ler_cad(c["caminho"], 3) == "SIM"


def test_solicitacoes_repetidas_na_tela_sao_processadas_uma_vez(cenario):
    site = SiteFake(solicitacoes={"BRUNO": ["1001"]}, dwgs={"1001": ["a.dwg"]})
    c = cenario([(222, "BRUNO", "X", None)], site)
    rodar(c)

    assert c["resumo"].sucesso == ["BRUNO (1001)"]  # o fake devolve a solicitação duplicada


def test_sessao_caida_na_triagem_interrompe_e_nao_marca_nada(cenario, ler_cad):
    """Regressão: antes o robô seguia rodando e marcava NÃO por engano."""
    site = SiteFake(cai_na_triagem={"FABIO"}, solicitacoes={"GISELE": ["1004"]}, dwgs={"1004": ["g.dwg"]})
    c = cenario([(222, "FABIO", "ARACATI", None), (333, "GISELE", "ARARIPE", None)], site)

    with pytest.raises(SessaoExpirada, match="Triagem: FABIO"):
        rodar(c)

    assert ler_cad(c["caminho"], 3) is None
    assert ler_cad(c["caminho"], 4) is None  # a linha seguinte nem foi processada


def test_sessao_caida_no_upload_interrompe_e_nao_marca(cenario, ler_cad):
    site = SiteFake(solicitacoes={"HELENA": ["1005"]}, cai_no_upload={"1005"})
    c = cenario([(222, "HELENA", "X", None)], site)

    with pytest.raises(SessaoExpirada, match="Upload: HELENA"):
        rodar(c)

    assert ler_cad(c["caminho"], 3) is None


def test_erro_na_consulta_deixa_em_branco_em_vez_de_marcar_nao(cenario, ler_cad):
    """Não dá para afirmar NÃO quando a consulta falhou: a linha fica para a próxima rodada."""
    site = SiteFake(solicitacoes={"IVO": ["1006"]}, falha_no_upload={"1006"})
    c = cenario([(222, "IVO", "X", None)], site)
    rodar(c)

    assert ler_cad(c["caminho"], 3) is None
    assert c["resumo"].erro == ["IVO (1006)"]


def test_retomada_nao_reprocessa_linhas_ja_marcadas(cenario, ler_cad):
    site = SiteFake(solicitacoes={"BRUNO": ["1001"]}, dwgs={"1001": ["a.dwg"]})
    c = cenario([(111, "ANA", "X", "SIM"), (222, "BRUNO", "X", None)], site)
    rodar(c)

    assert [p.cliente for p in c["pendentes"]] == ["BRUNO"]
    assert c["controle"].get("concluidos") == 2  # a já marcada conta no progresso
    assert ler_cad(c["caminho"], 3) == "SIM"


def test_parar_antes_do_primeiro_cliente_nao_marca_nada(cenario, ler_cad):
    site = SiteFake(solicitacoes={"BRUNO": ["1001"]}, dwgs={"1001": ["a.dwg"]})
    c = cenario([(222, "BRUNO", "X", None)], site)
    c["controle"].evt_parar.set()

    with pytest.raises(Interrompido):
        rodar(c)

    assert ler_cad(c["caminho"], 3) is None
    assert c["resumo"].sucesso == []
    assert c["resumo"].erro == []


def test_estado_expoe_cliente_ordem_e_solicitacao_em_analise(cenario):
    """O painel "Analisando agora" depende desses campos no snapshot."""
    site = SiteFake(solicitacoes={"BRUNO": ["1001"]}, dwgs={"1001": ["a.dwg"]})
    c = cenario([(222, "BRUNO", "SOBRAL", None)], site)
    vistos = []
    gravar = c["planilha"].gravar_cad

    def espiar(linha, valor):
        vistos.append(dict(c["controle"].snapshot()))
        gravar(linha, valor)

    c["planilha"].gravar_cad = espiar
    rodar(c)

    assert vistos[0]["cliente_atual"] == "BRUNO"
    assert str(vistos[0]["ordem_atual"]) == "222"
    assert vistos[0]["solicitacao_atual"] == "1001"
    assert vistos[0]["linha_atual"] == 3
    # Ao terminar, o painel não pode continuar mostrando o último cliente.
    assert c["controle"].get("cliente_atual") == ""
    assert c["controle"].get("ordem_atual") is None
    assert c["controle"].get("solicitacao_atual") == ""
