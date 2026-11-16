"""Orquestração da execução, compartilhada pela janela e pelos testes."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

from automacao import config
from automacao.alertas import avisar_sessao_caiu
from automacao.excecoes import Interrompido, SessaoExpirada
from automacao.formato import validar_planilha
from automacao.navegador import abrir_sessao_portal, conectar_chrome, garantir_chrome_aberto
from automacao.planilha import LinhaPendente, Planilha
from automacao.processador import processar_clientes
from automacao.resumo import Resumo


@dataclass
class Preparacao:
    """Tudo que foi validado/carregado antes de começar."""
    planilha: Planilha
    pendentes: list[LinhaPendente]
    ja_preenchidas: int
    caminho_excel: Path
    pasta_downloads: Path


@dataclass
class ResultadoExecucao:
    estado: str  # finalizado | sessao_caiu | parado | erro
    mensagem: str
    resumo: Resumo
    ja_preenchidas: int = 0
    total: int = 0


def preparar(caminho_excel, pasta_downloads, reprocessar_nao=False, limite_clientes=None) -> Preparacao:
    """Valida os caminhos, abre a planilha e devolve as linhas pendentes."""
    if not caminho_excel:
        raise ValueError("Escolha a planilha de controle (.xlsx).")
    if not pasta_downloads:
        raise ValueError("Escolha a pasta onde os DWG serão salvos.")

    caminho_excel = Path(caminho_excel)
    pasta_downloads = Path(pasta_downloads)

    if not caminho_excel.is_file():
        raise ValueError(f"A planilha não foi encontrada em: {caminho_excel}")
    if not pasta_downloads.is_dir():
        raise ValueError(
            f"A pasta de destino não existe: {pasta_downloads}. "
            "Escolha uma pasta que já exista (o robô não cria pastas)."
        )

    validacao = validar_planilha(caminho_excel)
    if not validacao.ok:
        raise ValueError(validacao.mensagem)

    planilha = Planilha(caminho_excel)
    pendentes, ja_preenchidas = planilha.carregar_pendentes(reprocessar_nao)
    if limite_clientes is not None:
        pendentes = pendentes[:limite_clientes]
    return Preparacao(planilha, pendentes, ja_preenchidas, caminho_excel, pasta_downloads)


def _finalizar(controle, resumo, preparacao, estado, mensagem) -> ResultadoExecucao:
    controle.set(estado=estado, mensagem=mensagem, fim=time.time(), cliente_atual="",
                 ordem_atual=None, solicitacao_atual="")
    # Só regrava a planilha se alguma linha foi marcada. Sem marcação, salvar de
    # novo poderia mexer na formatação à toa (e o openpyxl não preserva tudo).
    if controle.get("com_cad") or controle.get("sem_cad"):
        preparacao.planilha.salvar()
    resumo.imprimir()
    return ResultadoExecucao(
        estado=estado,
        mensagem=mensagem,
        resumo=resumo,
        ja_preenchidas=preparacao.ja_preenchidas,
        total=preparacao.ja_preenchidas + len(preparacao.pendentes),
    )


def executar(preparacao: Preparacao, controle, resumo: Resumo) -> ResultadoExecucao:
    """
    Executa o fluxo completo. Não mexe em Tkinter nem encerra o Chrome; quem
    chama cuida da janela. O Chrome não é fechado ao final.
    """
    pendentes = preparacao.pendentes
    ja_preenchidas = preparacao.ja_preenchidas
    total = ja_preenchidas + len(pendentes)

    controle.set(total_geral=total, concluidos=ja_preenchidas, ja_preenchidas=ja_preenchidas)
    if not pendentes:
        print("Nada a fazer: todas as linhas já estão com a coluna CAD preenchida.")
        return _finalizar(controle, resumo, preparacao, "finalizado",
                          "Todas as linhas já estão com a coluna CAD preenchida.")

    if ja_preenchidas:
        print(f"Continuando de onde parei: {len(pendentes)} cliente(s) para analisar "
              f"({ja_preenchidas} linha(s) já preenchida(s) serão puladas).")
    else:
        print(f"Começando: {len(pendentes)} cliente(s) para analisar.")

    try:
        garantir_chrome_aberto()
    except Exception as erro:
        print(f"Não consegui abrir o Chrome: {erro}")
        return _finalizar(controle, resumo, preparacao, "erro", str(erro))

    sessao_expirada = None
    interrompido = False

    try:
        with sync_playwright() as playwright:
            try:
                navegador = conectar_chrome(playwright)
            except Exception as erro:
                mensagem = (
                    "Não consegui conectar ao Chrome. Ele foi aberto com "
                    f"--remote-debugging-port={config.PORTA_CDP}? Detalhe: {erro}"
                )
                print(mensagem)
                return _finalizar(controle, resumo, preparacao, "erro", mensagem)

            try:
                contexto, pagina = abrir_sessao_portal(navegador, controle)
            except Interrompido:
                print("\nExecução interrompida antes de começar.")
                return _finalizar(controle, resumo, preparacao, "parado",
                                  "Interrompido antes de começar.")
            except Exception as erro:
                print(f"Não consegui abrir a sessão do portal: {erro}")
                return _finalizar(controle, resumo, preparacao, "erro", str(erro))

            print(f"Iniciando o download dos CAD de {len(pendentes)} cliente(s).")

            try:
                processar_clientes(
                    pendentes,
                    preparacao.planilha,
                    contexto,
                    pagina,
                    controle,
                    resumo,
                    pasta_downloads=preparacao.pasta_downloads,
                )
            except SessaoExpirada as erro:
                sessao_expirada = str(erro)
            except Interrompido:
                interrompido = True
                print("\nExecução interrompida. O progresso já está salvo na planilha.")
            except KeyboardInterrupt:
                interrompido = True
                print("\nExecução interrompida manualmente. "
                      "O progresso já está salvo na planilha.")
            except Exception as erro:
                print(f"Erro inesperado: {erro}")
                return _finalizar(controle, resumo, preparacao, "erro", str(erro))

        if sessao_expirada:
            avisar_sessao_caiu(sessao_expirada)
            return _finalizar(controle, resumo, preparacao, "sessao_caiu", sessao_expirada)
        if interrompido:
            return _finalizar(controle, resumo, preparacao, "parado",
                              "Interrompido pelo botão Parar.")
        print("\nExecução finalizada. Confira o resultado na planilha.")
        return _finalizar(controle, resumo, preparacao, "finalizado",
                          "Todas as linhas pendentes foram processadas.")

    except KeyboardInterrupt:
        print("\nExecução interrompida manualmente.")
        return _finalizar(controle, resumo, preparacao, "parado",
                          "Interrompido manualmente.")
    except Exception as erro:
        print(f"Erro inesperado: {erro}")
        return _finalizar(controle, resumo, preparacao, "erro", str(erro))
