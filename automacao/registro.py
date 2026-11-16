"""Log em arquivo e redirecionamento da saída do terminal para a janela.

O executável é windowed (`console=False`), então `sys.stdout` pode ser None.
Este módulo garante que todo `print` continue funcionando e apareça no log.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class _ControleHandler(logging.Handler):
    """Leva as linhas do logger para o painel de log da janela."""

    def __init__(self, controle):
        super().__init__()
        self.controle = controle

    def emit(self, record):
        try:
            self.controle.registrar_log(record.levelname, record.getMessage())
        except Exception:
            # Um erro de log nunca pode derrubar a automação.
            pass


def configurar(controle, pasta_logs):
    """(Re)configura o logger da execução e devolve o logger.

    `controle` pode ser None antes da primeira rodada: nesse caso o log vai
    apenas para o arquivo, sem painel na janela.
    """
    pasta = Path(pasta_logs)
    pasta.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("downloadercad")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    arquivo = RotatingFileHandler(
        pasta / "downloadercad.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    arquivo.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%d/%m/%Y %H:%M:%S"
    ))
    logger.addHandler(arquivo)
    if controle is not None:
        logger.addHandler(_ControleHandler(controle))
    return logger


class FluxoLog:
    """Substitui stdout/stderr: mantém o terminal (se houver) e alimenta o log."""

    encoding = "utf-8"
    errors = "replace"
    closed = False

    def __init__(self, logger, original=None):
        self._logger = logger
        self._original = original
        self._buffer = ""

    def write(self, texto):
        if not texto:
            return 0
        if self._original is not None:
            try:
                self._original.write(texto)
            except Exception:
                pass
        self._buffer += texto
        while "\n" in self._buffer:
            linha, self._buffer = self._buffer.split("\n", 1)
            if linha.strip():
                self._logger.info(linha.rstrip())
        return len(texto)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def writelines(self, linhas):
        for linha in linhas:
            self.write(linha)

    def isatty(self):
        return False

    def __getattr__(self, nome):
        if self._original is None:
            raise AttributeError(nome)
        return getattr(self._original, nome)


def redirecionar(logger):
    """Aponta stdout/stderr para o log. Pode ser chamado mais de uma vez."""
    if isinstance(sys.stdout, FluxoLog):
        original_out = sys.stdout._original
    else:
        original_out = sys.stdout if hasattr(sys.stdout, "write") else None
    if isinstance(sys.stderr, FluxoLog):
        original_err = sys.stderr._original
    else:
        original_err = sys.stderr if hasattr(sys.stderr, "write") else None
    sys.stdout = FluxoLog(logger, original_out)
    sys.stderr = FluxoLog(logger, original_err)
