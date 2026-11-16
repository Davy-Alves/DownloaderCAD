"""Exceções específicas da automação."""


class SessaoExpirada(Exception):
    """O portal derrubou a sessão: a execução inteira deve ser interrompida."""


class Interrompido(Exception):
    """O usuário pediu para parar pela janela (botão Parar)."""
