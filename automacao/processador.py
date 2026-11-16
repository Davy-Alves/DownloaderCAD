"""Orquestra o processamento: cliente a cliente, solicitação a solicitação."""
from automacao import apresentacao, config, portal
from automacao.excecoes import Interrompido, SessaoExpirada
from automacao.navegador import limpar_abas, mostrar_cookies, sessao_caiu
from automacao.utils import sanitizar_nome


def processar_clientes(pendentes, planilha, contexto, pagina, controle, resumo, pasta_downloads=None):
    """Processa todas as linhas pendentes. Levanta SessaoExpirada se a sessão cair."""
    pasta_downloads = pasta_downloads or config.PASTA_DOWNLOADS
    total = len(pendentes)
    base = controle.get("ja_preenchidas")

    for contador, pendente in enumerate(pendentes, start=1):
        controle.aguardar_se_pausado()
        if controle.parar_solicitado():
            raise Interrompido()
        controle.set(
            concluidos=base + contador - 1,
            cliente_atual=pendente.cliente,
            ordem_atual=pendente.ordem,
            solicitacao_atual="",
            linha_atual=pendente.linha_excel,
        )
        print(f"{apresentacao.MARCA_DESTAQUE}Cliente {contador} de {total}: "
              f"{pendente.cliente} — Ordem {pendente.ordem} "
              f"(linha {pendente.linha_excel} da planilha)")

        _processar_cliente(
            pendente, planilha, contexto, pagina, controle, resumo, pasta_downloads
        )

    controle.set(
        concluidos=base + total,
        cliente_atual="",
        ordem_atual=None,
        solicitacao_atual="",
        linha_atual=None,
    )


def _processar_cliente(pendente, planilha, contexto, pagina, controle, resumo, pasta_downloads):
    if not portal.abrir_triagem(pagina, pendente.cliente, pendente.municipio):
        print("  Não consegui carregar a triagem deste cliente.")
        resumo.erro.append(pendente.cliente)
        return

    # Sessão caiu na Triagem: para TUDO (não marca NÃO por engano)
    if sessao_caiu(pagina, "triagem.aspx"):
        raise SessaoExpirada(f"Triagem: {pendente.cliente} (linha {pendente.linha_excel})")

    solicitacoes = portal.extrair_solicitacoes(pagina)
    if not solicitacoes:
        print("  Nenhuma solicitação encontrada: a planilha será marcada com NÃO.")
        resumo.sem_cad.append(f"{pendente.cliente} (sem solicitação)")
        _marcar_cad(planilha, controle, pendente, "NÃO", "")
        return

    if len(solicitacoes) == 1:
        print(f"  1 solicitação encontrada: {solicitacoes[0]}.")
    else:
        print(f"  {len(solicitacoes)} solicitações encontradas: "
              f"{apresentacao.listar_solicitacoes(solicitacoes)}.")

    encontrou_cad = False
    houve_erro = False
    for num_solicitud in solicitacoes:
        controle.aguardar_se_pausado()
        if controle.parar_solicitado():
            raise Interrompido()
        controle.set(solicitacao_atual=num_solicitud)
        tem_dwg, deu_erro = _processar_solicitacao(
            num_solicitud, pendente, contexto, pagina, resumo, pasta_downloads
        )
        encontrou_cad = encontrou_cad or tem_dwg
        houve_erro = houve_erro or deu_erro

    if not encontrou_cad:
        resumo.sem_cad.append(pendente.cliente)

    # Marca a planilha. Se houve erro e nada foi encontrado, deixa em branco
    # (não dá para afirmar "NÃO" quando a consulta falhou).
    if encontrou_cad:
        _marcar_cad(planilha, controle, pendente, "SIM", ", ".join(solicitacoes))
    elif not houve_erro:
        _marcar_cad(planilha, controle, pendente, "NÃO", ", ".join(solicitacoes))
    else:
        print("  A planilha não foi alterada: houve erro na consulta, "
              "então esta linha será refeita na próxima rodada.")


def _processar_solicitacao(num_solicitud, pendente, contexto, pagina, resumo, pasta_downloads):
    """
    Baixa o DWG mais recente de uma solicitação.
    Retorna (tem_dwg, deu_erro). Levanta SessaoExpirada se a sessão cair.
    """
    destino = (
        pasta_downloads
        / sanitizar_nome(pendente.cliente)
        / sanitizar_nome(pendente.ordem)
        / sanitizar_nome(num_solicitud)
    )

    if destino.exists() and any(f.name.lower().endswith(".dwg") for f in destino.iterdir()):
        print(f"  Solicitação {num_solicitud}: o DWG já está na pasta de destino, "
              "nada a baixar.")
        resumo.pulados.append(f"{pendente.cliente} ({num_solicitud})")
        return True, False

    aba = None
    tem_dwg = False
    try:
        mostrar_cookies(contexto, f"ANTES UPLOAD {num_solicitud}")
        aba = portal.abrir_upload(contexto, pagina, num_solicitud)
        aba.wait_for_timeout(3000)

        # Sessão caiu no Upload: para TUDO
        if sessao_caiu(aba, "upload.aspx"):
            if not aba.is_closed():
                aba.close()
            raise SessaoExpirada(
                f"Upload: {pendente.cliente} (linha {pendente.linha_excel}, "
                f"solicitação {num_solicitud})"
            )

        links = portal.localizar_links_dwg(aba)
        if not links:
            print(f"  Solicitação {num_solicitud}: nenhum DWG disponível.")
            aba.close()
            return False, False

        tem_dwg = True
        link = links[-1]  # considera o último da lista como o mais recente
        nome = link.inner_text().strip()
        print(f"  Solicitação {num_solicitud}: baixando {nome}...")

        caminho = portal.baixar_dwg(aba, link, destino)
        print(f"  Solicitação {num_solicitud}: arquivo salvo em {caminho}")
        resumo.sucesso.append(f"{pendente.cliente} ({num_solicitud})")

        aba.close()
        return True, False

    except SessaoExpirada:
        raise  # não tratar como erro comum: propaga e interrompe a execução
    except Interrompido:
        if aba is not None and not aba.is_closed():
            aba.close()
        raise
    except Exception as e:
        print(f"  Solicitação {num_solicitud}: erro na consulta — {e}")
        resumo.erro.append(f"{pendente.cliente} ({num_solicitud})")
        if aba is not None and not aba.is_closed():
            aba.close()
        return tem_dwg, True
    finally:
        limpar_abas(contexto, pagina)


def _marcar_cad(planilha, controle, pendente, valor, solicitacao=""):
    planilha.gravar_cad(pendente.linha_excel, valor)
    controle.contar(valor)
    # A linha "Planilha atualizada..." é registrada por registrar_alteracao;
    # não imprimir de novo aqui (antes aparecia duas vezes no log).
    controle.registrar_alteracao(
        pendente.linha_excel, pendente.cliente, pendente.ordem, solicitacao, valor
    )
