"""Ponto de entrada do Downloader CAD: abre a janela local."""
from __future__ import annotations

import traceback
from pathlib import Path

from automacao import config, janela


def _registrar_falha(erro: Exception) -> Path | None:
    """Grava uma falha de inicialização num arquivo, sem depender do terminal."""
    try:
        pasta = Path(config.PASTA_LOGS)
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / "falha-inicializacao.log"
        caminho.write_text(traceback.format_exc(), encoding="utf-8")
        return caminho
    except Exception:
        return None


def main():
    try:
        janela.iniciar()
    except Exception as erro:
        caminho = _registrar_falha(erro)
        detalhe = f"\n\nDetalhes salvos em:\n{caminho}" if caminho else ""
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Downloader CAD",
                f"Não consegui abrir o aplicativo:\n{erro}{detalhe}",
            )
            root.destroy()
        except Exception:
            # Último recurso quando nem o Tkinter está disponível.
            pass


if __name__ == "__main__":
    main()
