"""Alertas para o usuário."""


def tocar_alerta():
    """Toca bipes no Windows para chamar a atenção do usuário."""
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 600)
    except Exception:
        pass


def avisar_sessao_caiu(detalhe):
    """Toca o alerta e registra o aviso no log (a janela mostra o diálogo)."""
    tocar_alerta()

    print("\n" + "!" * 60)
    print("!!!  A SESSÃO DO PORTAL CAIU - EXECUÇÃO INTERROMPIDA  !!!")
    print("!" * 60)
    print(f"Onde parou: {detalhe}")
    print("Esse cliente NÃO foi marcado na planilha (ficou em branco).")
    print("\nPara continuar de onde parou:")
    print("  1. No Chrome, faça login novamente e escolha o perfil de acesso")
    print("  2. Clique em Iniciar para rodar outra vez (ele pula o que já está marcado em CAD)")
    print("!" * 60)
