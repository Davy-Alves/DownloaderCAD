"""Estado da execução compartilhado entre a janela e o robô.

Nada aqui conhece Tkinter ou Playwright: a janela lê `snapshot()` e o robô
chama os métodos de progresso. Isso mantém a lógica testável e evita que a
thread de automação toque na interface.
"""
from __future__ import annotations

import collections
import csv
import threading
import time
from pathlib import Path

from automacao.excecoes import Interrompido


class Controle:
    """Guarda estado, eventos, log e histórico de alterações da planilha."""

    def __init__(self, resumo, historico_path=None, espera: float = 0.2):
        self._resumo = resumo
        self._lock = threading.Lock()
        self._log = collections.deque(maxlen=500)
        self._log_seq = 0
        self._historico_path = Path(historico_path) if historico_path else None
        self._espera = espera
        self._estado = {
            "estado": "ocioso",
            "mensagem": "",
            "total_geral": 0,
            "concluidos": 0,
            "ja_preenchidas": 0,
            "cliente_atual": "",
            "ordem_atual": None,
            "solicitacao_atual": "",
            "linha_atual": None,
            "com_cad": 0,
            "sem_cad": 0,
            "inicio": None,
            "fim": None,
        }
        self.evt_iniciar = threading.Event()  # setado por "Já estou logado"
        self.evt_pausar = threading.Event()   # setado = pausa solicitada
        self.evt_parar = threading.Event()    # setado pelo botão Parar

    # --- Estado -------------------------------------------------------------
    def set(self, **campos):
        with self._lock:
            self._estado.update(campos)

    def get(self, chave):
        with self._lock:
            return self._estado[chave]

    def contar(self, valor):
        """Conta uma marcação feita na planilha (SIM/NÃO)."""
        with self._lock:
            if valor == "SIM":
                self._estado["com_cad"] += 1
            elif valor == "NÃO":
                self._estado["sem_cad"] += 1

    def registrar_log(self, nivel: str, mensagem: str):
        nivel = str(nivel).upper()
        if nivel == "WARNING":
            nivel = "AVISO"
        elif nivel == "CRITICAL":
            nivel = "ERRO"
        with self._lock:
            self._log_seq += 1
            self._log.append({
                "seq": self._log_seq,
                "hora": time.strftime("%H:%M:%S"),
                "nivel": nivel,
                "texto": str(mensagem),
            })

    def registrar_alteracao(self, linha, cliente, ordem, solicitacao, resultado, detalhe=""):
        """Registra uma mudança real feita na planilha (histórico em CSV)."""
        cabeca = f"Planilha atualizada: CAD = {resultado} — {cliente}"
        extras = []
        if ordem not in (None, ""):
            extras.append(f"Ordem {ordem}")
        if solicitacao not in (None, ""):
            extras.append(f"Solicitação {solicitacao}")
        texto = cabeca + (" · " + " · ".join(extras) if extras else "")
        self.registrar_log("OK", texto)
        if self._historico_path is None:
            return
        try:
            self._historico_path.parent.mkdir(parents=True, exist_ok=True)
            novo = not self._historico_path.exists() or self._historico_path.stat().st_size == 0
            with self._historico_path.open(
                "a", newline="", encoding="utf-8-sig" if novo else "utf-8"
            ) as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                if novo:
                    escritor.writerow([
                        "data_hora", "linha", "cliente", "ordem",
                        "solicitacao", "resultado", "detalhe",
                    ])
                escritor.writerow([
                    time.strftime("%d/%m/%Y %H:%M:%S"),
                    linha, cliente, ordem or "", solicitacao or "", resultado, detalhe,
                ])
        except OSError as erro:
            self.registrar_log("AVISO", f"Não consegui gravar o histórico de alterações: {erro}")

    def snapshot(self):
        with self._lock:
            estado = dict(self._estado)
            estado["log"] = list(self._log)
            estado["log_seq"] = self._log_seq
        estado["baixados"] = len(self._resumo.sucesso)
        estado["erros"] = len(self._resumo.erro)
        estado["pulados"] = len(self._resumo.pulados)
        estado["pausa_solicitada"] = self.evt_pausar.is_set()
        estado["decorrido"] = (
            int((estado["fim"] or time.time()) - estado["inicio"]) if estado["inicio"] else 0
        )
        return estado

    def limpar_log(self):
        with self._lock:
            self._log.clear()
            self._log_seq = 0

    # --- Controle de execução ----------------------------------------------
    def parar_solicitado(self) -> bool:
        return self.evt_parar.is_set()

    def aguardar_inicio(self):
        """Espera o clique em 'Já estou logado'."""
        while not self.evt_iniciar.is_set():
            if self.evt_parar.is_set():
                raise Interrompido()
            time.sleep(self._espera)

    def aguardar_se_pausado(self):
        """Se Pausar foi clicado, espera aqui até clicar em Retomar."""
        if not self.evt_pausar.is_set():
            return
        self.set(estado="pausado")
        print("Execução pausada. Clique em Retomar para continuar.")
        while self.evt_pausar.is_set():
            if self.evt_parar.is_set():
                self.evt_pausar.clear()
                raise Interrompido()
            time.sleep(self._espera)
        self.set(estado="executando")
        print("Continuando de onde parou.")

    def reiniciar(self):
        """Prepara uma nova rodada sem apagar o log da tela."""
        self.evt_iniciar.clear()
        self.evt_pausar.clear()
        self.evt_parar.clear()
        with self._lock:
            self._estado.update({
                "estado": "ocioso",
                "mensagem": "",
                "total_geral": 0,
                "concluidos": 0,
                "ja_preenchidas": 0,
                "cliente_atual": "",
                "ordem_atual": None,
                "solicitacao_atual": "",
                "linha_atual": None,
                "com_cad": 0,
                "sem_cad": 0,
                "inicio": None,
                "fim": None,
            })
