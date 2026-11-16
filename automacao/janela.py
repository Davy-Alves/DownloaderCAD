"""Janela principal do Downloader CAD (Tkinter)."""
from __future__ import annotations

import os
import logging
import threading
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from automacao import apresentacao, config, registro, textos
from automacao.controle import Controle
from automacao.execucao import executar, preparar
from automacao.formato import gerar_modelo, texto_formato, validar_destino, validar_planilha
from automacao.resumo import Resumo


class Aplicativo:
    """Monta a interface e coordena a thread de automação."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.controle = None
        self.resumo = None
        self.worker = None
        self.planilha = None
        self.destino = None
        self.validacao = None
        self._logger = None
        self._log_seq_visto = 0
        self._ultimo_estado = "ocioso"
        self._finalizar_pendente = False
        self._fechando = False
        self._logger = registro.configurar(None, config.PASTA_LOGS)
        registro.redirecionar(self._logger)
        self._registrar("INFO", "Downloader CAD iniciado.")

        self._configurar_janela()
        self._montar()
        self._carregar_preferencias()
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.root.after(300, self._primeiro_uso)
        self.root.after(200, self._atualizar)

    # --- Construção da tela -------------------------------------------------
    def _configurar_janela(self):
        self.root.title("Downloader CAD")
        # A janela é DPI-virtualizada pelo Windows, então o tamanho em pixels já
        # sai proporcional à escala da tela. A altura vem da tela (descontando
        # título e barra de tarefas) e o topo é fixo: na posição cascata padrão
        # do Tk o rodapé cai atrás da barra de tarefas em 1080p a 125%.
        altura = apresentacao.altura_da_janela(self.root.winfo_screenheight())
        self.root.geometry(f"940x{altura}+40+20")
        self.root.minsize(820, 640)
        try:
            ttk.Style().theme_use("vista")
        except tk.TclError:
            pass
        estilo = ttk.Style()
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 16, "bold"))
        estilo.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        estilo.configure("Foco.TLabel", font=("Segoe UI", 10, "bold"), foreground="#111827")
        estilo.configure("Dica.TLabel", foreground="#6b7280")
        estilo.configure("Aviso.TLabel", foreground="#b45309")
        estilo.configure("Erro.TLabel", foreground="#b91c1c")
        estilo.configure("Ok.TLabel", foreground="#15803d")
        estilo.configure("Campo.TEntry", padding=(6, 5))

    # --- Botões -------------------------------------------------------------
    # O tema "vista" do ttk ignora cor de fundo em TButton, então os botões são
    # tk.Button "flat": é o que permite primário azul, perigo vermelho e um
    # desabilitado realmente apagado.
    def _criar_botao(self, pai, texto, comando, *, compacto=False,
                     largura=None, nivel="secundario"):
        """Cria um botão já com o padrão visual da tela.

        `compacto` usa a altura dos campos (~30 px); sem ele, altura de ação
        (~40 px). `largura` é em caracteres e serve para igualar botões irmãos.
        """
        botao = tk.Button(
            pai,
            text=texto,
            command=comando,
            font=("Segoe UI", 9) if compacto else ("Segoe UI", 10, "bold"),
            padx=12 if compacto else 14,
            pady=5 if compacto else 8,
            relief="flat",
            bd=0,
            highlightthickness=1,
            cursor="arrow",
        )
        if largura:
            botao.configure(width=largura)
        self._aplicar_aparencia(botao, nivel, True)
        botao.bind("<Enter>", lambda _evento, b=botao: self._pintar_hover(b))
        botao.bind("<Leave>", lambda _evento, b=botao: self._pintar_saida(b))
        return botao

    def _aplicar_aparencia(self, botao, nivel, habilitado):
        """Aplica estado e nível visual, guardando as cores para hover/foco."""
        cores = apresentacao.PALETA["desabilitado" if not habilitado else nivel]
        botao._nivel = nivel
        botao._habilitado = habilitado
        botao._cor_normal = cores["fundo"]
        botao._cor_hover = cores["hover"]
        botao.configure(
            state="normal" if habilitado else "disabled",
            bg=cores["fundo"],
            fg=cores["texto"],
            activebackground=cores["pressionado"],
            activeforeground=cores["texto"],
            disabledforeground=apresentacao.PALETA["desabilitado"]["texto"],
            highlightbackground=cores["borda"],
            highlightcolor=cores["foco"],
            cursor="arrow" if habilitado else "no",
        )

    @staticmethod
    def _pintar_hover(botao):
        if getattr(botao, "_habilitado", False):
            botao.configure(bg=botao._cor_hover)

    @staticmethod
    def _pintar_saida(botao):
        if getattr(botao, "_habilitado", False):
            botao.configure(bg=botao._cor_normal)

    def _montar(self):
        container = ttk.Frame(self.root, padding=14)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        topo = ttk.Frame(container)
        topo.grid(row=0, column=0, sticky="we", pady=(0, 10))
        topo.columnconfigure(0, weight=1)
        ttk.Label(topo, text="Downloader CAD", style="Titulo.TLabel").grid(row=0, column=0, sticky="w")

        # Selo de status: fundo colorido por estado (Tk não arredonda cantos).
        self.lbl_status = tk.Label(
            topo,
            text=apresentacao.ROTULOS_ESTADO["ocioso"],
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg=apresentacao.CORES_ESTADO["ocioso"],
            padx=10,
            pady=4,
        )
        self.lbl_status.grid(row=0, column=1, sticky="e", padx=(8, 14))

        self.btn_ajuda = self._criar_botao(
            topo, "Como usar", self._como_usar, compacto=True, largura=14
        )
        self.btn_ajuda.grid(row=0, column=2, padx=(0, 6))
        self.btn_config = self._criar_botao(
            topo, "Configurações", self._configuracoes, compacto=True, largura=14
        )
        self.btn_config.grid(row=0, column=3)

        # Passo 1: planilha e destino
        caixa1 = ttk.LabelFrame(container, text="1. Planilha e pasta de destino", padding=10)
        caixa1.grid(row=1, column=0, sticky="we", pady=(0, 8))
        caixa1.columnconfigure(1, weight=1)

        self.var_planilha = tk.StringVar()
        self.var_destino = tk.StringVar()
        self.var_validacao = tk.StringVar(value="Escolha a planilha para começar.")
        ttk.Label(caixa1, text="Planilha:").grid(row=0, column=0, sticky="w")
        ttk.Entry(caixa1, textvariable=self.var_planilha, state="readonly",
                  style="Campo.TEntry").grid(row=0, column=1, sticky="we", padx=8)
        self.btn_carregar = self._criar_botao(
            caixa1, "Carregar planilha", self._carregar_planilha,
            compacto=True, largura=18,
        )
        self.btn_carregar.grid(row=0, column=2, sticky="e")

        ttk.Label(caixa1, text="Pasta dos DWG:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(caixa1, textvariable=self.var_destino, state="readonly",
                  style="Campo.TEntry").grid(row=1, column=1, sticky="we", padx=8, pady=(8, 0))
        self.btn_pasta = self._criar_botao(
            caixa1, "Alterar pasta", self._alterar_pasta,
            compacto=True, largura=18,
        )
        self.btn_pasta.grid(row=1, column=2, sticky="e", pady=(8, 0))

        self.lbl_validacao = ttk.Label(caixa1, textvariable=self.var_validacao, style="Dica.TLabel",
                                       wraplength=820)
        self.lbl_validacao.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        atalhos = ttk.Frame(caixa1)
        atalhos.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self.btn_modelo = self._criar_botao(
            atalhos, "Baixar modelo de planilha", self._baixar_modelo,
            compacto=True, largura=26,
        )
        self.btn_modelo.grid(row=0, column=0, padx=(0, 8))
        self.btn_formato = self._criar_botao(
            atalhos, "Ver formato aceito", self._ver_formato,
            compacto=True, largura=26,
        )
        self.btn_formato.grid(row=0, column=1)

        # Passo 2: execução
        caixa2 = ttk.LabelFrame(container, text="2. Login e execução", padding=10)
        caixa2.grid(row=2, column=0, sticky="we", pady=(0, 8))
        caixa2.columnconfigure(0, weight=1)

        self.var_instrucao = tk.StringVar(
            value="Clique em Iniciar. O Chrome abrirá no portal; faça o login e depois "
                  "clique em \"Já estou logado\"."
        )
        ttk.Label(caixa2, textvariable=self.var_instrucao, style="Dica.TLabel",
                  wraplength=860).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Dois grupos: à esquerda o fluxo de início, à direita o controle da
        # execução. `uniform` deixa todos os botões do grupo com a mesma largura.
        linha_exec = ttk.Frame(caixa2)
        linha_exec.grid(row=1, column=0, sticky="we")
        linha_exec.columnconfigure(1, weight=1)

        grupo_inicio = ttk.Frame(linha_exec)
        grupo_inicio.grid(row=0, column=0, sticky="w")
        grupo_inicio.columnconfigure(0, weight=1, uniform="inicio")
        grupo_inicio.columnconfigure(1, weight=1, uniform="inicio")

        self.btn_iniciar = self._criar_botao(grupo_inicio, "Iniciar", self._iniciar)
        self.btn_iniciar.grid(row=0, column=0, sticky="ew", padx=4)
        self.btn_login = self._criar_botao(
            grupo_inicio, "Já estou logado", self._ja_fiz_login
        )
        self.btn_login.grid(row=0, column=1, sticky="ew", padx=4)

        grupo_controle = ttk.Frame(linha_exec)
        grupo_controle.grid(row=0, column=2, sticky="e", padx=(12, 0))
        for coluna in range(4):
            grupo_controle.columnconfigure(coluna, weight=1, uniform="controle")

        self.btn_pausar = self._criar_botao(grupo_controle, "Pausar", self._pausar)
        self.btn_retomar = self._criar_botao(grupo_controle, "Retomar", self._retomar)
        self.btn_parar = self._criar_botao(grupo_controle, "Parar", self._parar)
        self.btn_finalizar = self._criar_botao(grupo_controle, "Finalizar", self._finalizar)
        for coluna, botao in enumerate([
            self.btn_pausar, self.btn_retomar, self.btn_parar, self.btn_finalizar,
        ]):
            botao.grid(row=0, column=coluna, sticky="ew", padx=4)

        caixa3 = ttk.LabelFrame(container, text="Progresso", padding=10)
        caixa3.grid(row=3, column=0, sticky="we", pady=(0, 8))
        caixa3.columnconfigure(0, weight=1)

        linha = ttk.Frame(caixa3)
        linha.grid(row=0, column=0, sticky="we")
        linha.columnconfigure(0, weight=1)
        ttk.Label(linha, text="Clientes processados").grid(row=0, column=0, sticky="w")
        self.var_progresso = tk.StringVar(value="0 / 0")
        ttk.Label(linha, textvariable=self.var_progresso, style="Status.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        self.progresso = ttk.Progressbar(caixa3, maximum=100, value=0)
        self.progresso.grid(row=1, column=0, sticky="we", pady=(4, 6))

        # "Analisando agora": o cliente em destaque e, abaixo, ordem,
        # solicitação e linha da planilha — os mesmos termos que o usuário vê
        # na planilha de controle.
        self.var_analise_foco = tk.StringVar(value="Aguardando o início")
        ttk.Label(caixa3, textvariable=self.var_analise_foco, style="Foco.TLabel",
                  wraplength=860).grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.var_analise_detalhe = tk.StringVar(
            value='Escolha a planilha e clique em "Iniciar".'
        )
        ttk.Label(caixa3, textvariable=self.var_analise_detalhe, style="Dica.TLabel",
                  wraplength=860).grid(row=3, column=0, sticky="w")

        chips = ttk.Frame(caixa3)
        chips.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.var_baixados = tk.StringVar(value="0 baixados")
        self.var_com_cad = tk.StringVar(value="0 com CAD")
        self.var_sem_cad = tk.StringVar(value="0 sem CAD")
        self.var_pulados = tk.StringVar(value="0 já existiam")
        self.var_erros = tk.StringVar(value="0 erros")
        for coluna, (var, cor) in enumerate([
            (self.var_baixados, "#dcfce7"),
            (self.var_com_cad, "#dcfce7"),
            (self.var_sem_cad, "#f3f4f6"),
            (self.var_pulados, "#f3f4f6"),
            (self.var_erros, "#fee2e2"),
        ]):
            ttk.Label(chips, textvariable=var, background=cor, padding=(8, 3)).grid(
                row=0, column=coluna, padx=(0, 6)
            )

        caixa4 = ttk.LabelFrame(container, text="Log", padding=10)
        caixa4.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
        caixa4.columnconfigure(0, weight=1)
        caixa4.rowconfigure(0, weight=1)

        self.log_text = tk.Text(caixa4, height=8, wrap="word", state="disabled",
                                font=("Consolas", 9), background="#f9fafb")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        rolagem = ttk.Scrollbar(caixa4, orient="vertical", command=self.log_text.yview)
        rolagem.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=rolagem.set)
        self.log_text.tag_configure("INFO", foreground="#374151")
        self.log_text.tag_configure("DESTAQUE", foreground="#1d4ed8",
                                    font=("Consolas", 9, "bold"))
        self.log_text.tag_configure("OK", foreground="#15803d")
        self.log_text.tag_configure("AVISO", foreground="#b45309")
        self.log_text.tag_configure("ERRO", foreground="#b91c1c")

        rodape_log = ttk.Frame(caixa4)
        rodape_log.grid(row=1, column=0, columnspan=2, sticky="we", pady=(8, 0))
        self.btn_logs = self._criar_botao(
            rodape_log, "Abrir pasta de logs", self._abrir_pasta_logs,
            compacto=True, largura=19,
        )
        self.btn_logs.grid(row=0, column=0, sticky="w")
        self.var_rodape = tk.StringVar(value="")
        ttk.Label(rodape_log, textvariable=self.var_rodape, style="Dica.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        rodape_log.columnconfigure(1, weight=1)

        # Mantém as referências para habilitar/desabilitar
        self.botoes = {
            "carregar": self.btn_carregar,
            "pasta": self.btn_pasta,
            "config": self.btn_config,
            "iniciar": self.btn_iniciar,
            "login": self.btn_login,
            "pausar": self.btn_pausar,
            "retomar": self.btn_retomar,
            "parar": self.btn_parar,
            "finalizar": self.btn_finalizar,
        }

    # --- Preferências -------------------------------------------------------
    def _carregar_preferencias(self):
        try:
            config.carregar_config()
        except ValueError as erro:
            messagebox.showerror(
                "Configuração",
                f"{erro}\n\nO aplicativo vai usar os valores padrão. "
                "Abra Configurações para corrigir.",
                parent=self.root,
            )

        if config.CAMINHO_EXCEL and Path(config.CAMINHO_EXCEL).is_file():
            self.planilha = Path(config.CAMINHO_EXCEL)
        if config.PASTA_DOWNLOADS and Path(config.PASTA_DOWNLOADS).is_dir():
            self.destino = Path(config.PASTA_DOWNLOADS)

        self.var_planilha.set(str(self.planilha) if self.planilha else "")
        self.var_destino.set(str(self.destino) if self.destino else "")
        if self.planilha and self.destino:
            self._validar_selecao(mostrar=False)
        self._atualizar_botoes()

    def _primeiro_uso(self):
        if not config.URL_PORTAL:
            messagebox.showinfo(
                "Bem-vindo ao Downloader CAD",
                textos.BOAS_VINDAS,
                parent=self.root,
            )
            self._configuracoes(primeiro_uso=True)
        elif not self.planilha:
            self.var_analise_foco.set("Aguardando o início")
            self.var_analise_detalhe.set(
                "Escolha a planilha e a pasta de destino. Se precisar, baixe o modelo."
            )

    # --- Seleção de planilha e destino -------------------------------------
    def _carregar_planilha(self):
        inicial = str(self.planilha.parent) if self.planilha else str(Path.home())
        caminho = filedialog.askopenfilename(
            parent=self.root,
            title="Escolha a planilha de controle",
            initialdir=inicial,
            filetypes=[("Planilha do Excel", "*.xlsx")],
        )
        if not caminho:
            return
        self.planilha = Path(caminho)
        self.var_planilha.set(str(self.planilha))
        self._registrar("INFO", f"Planilha escolhida: {self.planilha}")

        # O usuário escolhe a pasta de destino na mesma ação.
        if not self._escolher_destino():
            if not self.destino:
                messagebox.showwarning(
                    "Pasta de destino",
                    "Escolha a pasta onde os DWG serão salvos para poder iniciar.",
                    parent=self.root,
                )
        self._salvar_selecao()
        self._validar_selecao(mostrar=True)
        self._atualizar_botoes()

    def _alterar_pasta(self):
        if not self._escolher_destino():
            return
        self._salvar_selecao()
        self._validar_selecao(mostrar=True)
        self._atualizar_botoes()

    def _escolher_destino(self) -> bool:
        inicial = str(self.destino) if self.destino and Path(self.destino).is_dir() else str(Path.home())
        pasta = filedialog.askdirectory(
            parent=self.root,
            title="Escolha a pasta onde os DWG serão salvos",
            initialdir=inicial,
            mustexist=True,
        )
        if not pasta:
            return False
        self.destino = Path(pasta)
        self.var_destino.set(str(self.destino))
        self._registrar("INFO", f"Pasta de destino: {self.destino}")
        return True

    def _salvar_selecao(self):
        try:
            config.salvar_config(planilha=self.planilha, pasta_downloads=self.destino)
            config.CAMINHO_EXCEL = self.planilha
            config.PASTA_DOWNLOADS = self.destino
        except (OSError, ValueError) as erro:
            messagebox.showwarning(
                "Configuração",
                f"Não consegui salvar a seleção: {erro}",
                parent=self.root,
            )

    def _validar_selecao(self, mostrar=False):
        self.validacao = None
        if not self.planilha or not self.destino:
            self.var_validacao.set("Escolha a planilha e a pasta de destino.")
            self.lbl_validacao.configure(style="Dica.TLabel")
            return None

        ok_destino, mensagem_destino = validar_destino(self.destino)
        resultado = validar_planilha(self.planilha)

        if not ok_destino or not resultado.ok:
            mensagem = mensagem_destino if not ok_destino else resultado.mensagem
            self.var_validacao.set(mensagem)
            self.lbl_validacao.configure(style="Erro.TLabel")
            if mostrar:
                resposta = messagebox.askyesno(
                    "Não foi possível usar essa seleção",
                    f"{mensagem}\n\nDeseja baixar um modelo de planilha?",
                    parent=self.root,
                )
                if resposta:
                    self._baixar_modelo()
            return resultado

        self.validacao = resultado
        avisos = ("\n" + "\n".join(resultado.avisos)) if resultado.avisos else ""
        self.var_validacao.set(resultado.mensagem + avisos)
        self.lbl_validacao.configure(style="Aviso.TLabel" if resultado.avisos else "Ok.TLabel")
        if mostrar:
            if resultado.avisos:
                messagebox.showwarning("Planilha validada", resultado.mensagem + avisos,
                                       parent=self.root)
            else:
                messagebox.showinfo("Planilha validada", resultado.mensagem, parent=self.root)
        return resultado

    # --- Modelo e ajuda -----------------------------------------------------
    def _baixar_modelo(self):
        destino = filedialog.asksaveasfilename(
            parent=self.root,
            title="Salvar modelo de planilha",
            defaultextension=".xlsx",
            initialfile="modelo_planilha.xlsx",
            filetypes=[("Planilha do Excel", "*.xlsx")],
        )
        if not destino:
            return
        try:
            caminho = gerar_modelo(destino)
        except Exception as erro:
            messagebox.showerror("Modelo de planilha", f"Não consegui gerar o modelo: {erro}",
                                 parent=self.root)
            return
        if messagebox.askyesno(
            "Modelo salvo",
            f"Modelo salvo em:\n{caminho}\n\nDeseja abrir a pasta?",
            parent=self.root,
        ):
            self._abrir_pasta(caminho.parent)

    def _ver_formato(self):
        self._dialogo_texto("Formato aceito", texto_formato(), mostrar_modelo=True)

    def _como_usar(self):
        self._dialogo_texto(
            "Como usar o Downloader CAD",
            textos.AJUDA + "\n\n" + texto_formato(),
            mostrar_modelo=True,
        )

    def _dialogo_texto(self, titulo, conteudo, mostrar_modelo=False):
        janela = tk.Toplevel(self.root)
        janela.title(titulo)
        janela.transient(self.root)
        janela.grab_set()
        janela.geometry("820x620")
        janela.columnconfigure(0, weight=1)
        janela.rowconfigure(0, weight=1)

        quadro = ttk.Frame(janela, padding=12)
        quadro.grid(row=0, column=0, sticky="nsew")
        quadro.columnconfigure(0, weight=1)
        quadro.rowconfigure(0, weight=1)

        texto = tk.Text(quadro, wrap="word", width=90, height=28, font=("Segoe UI", 10))
        texto.grid(row=0, column=0, sticky="nsew")
        rolagem = ttk.Scrollbar(quadro, orient="vertical", command=texto.yview)
        rolagem.grid(row=0, column=1, sticky="ns")
        texto.configure(yscrollcommand=rolagem.set)
        texto.insert("1.0", conteudo)
        texto.configure(state="disabled")

        botoes = ttk.Frame(quadro)
        botoes.grid(row=1, column=0, columnspan=2, sticky="e", pady=(10, 0))
        if mostrar_modelo:
            self._criar_botao(
                botoes, "Baixar modelo", self._baixar_modelo, compacto=True, largura=16
            ).grid(row=0, column=0, padx=(0, 8))
        self._criar_botao(
            botoes, "Fechar", janela.destroy, compacto=True, largura=16, nivel="primario"
        ).grid(row=0, column=1)

    # --- Configurações ------------------------------------------------------
    def _configuracoes(self, primeiro_uso=False):
        janela = tk.Toplevel(self.root)
        janela.title("Configurações")
        janela.transient(self.root)
        janela.grab_set()
        janela.resizable(False, False)

        quadro = ttk.Frame(janela, padding=16)
        quadro.grid(row=0, column=0, sticky="nsew")
        quadro.columnconfigure(1, weight=1)

        linha = 0
        if primeiro_uso:
            ttk.Label(
                quadro,
                text=textos.BOAS_VINDAS,
                wraplength=560,
                justify="left",
            ).grid(row=linha, column=0, columnspan=3, sticky="w", pady=(0, 12))
            linha += 1

        var_url = tk.StringVar(value=config.URL_PORTAL)
        var_perfil = tk.StringVar(value=config.PERFIL_LOGIN)
        var_chrome = tk.StringVar(value=str(config.CHROME_EXE) if config.CHROME_EXE else "")
        var_porta = tk.StringVar(value=str(config.PORTA_CDP))
        var_limite = tk.StringVar(
            value="" if config.LIMITE_CLIENTES is None else str(config.LIMITE_CLIENTES)
        )
        var_reproc = tk.BooleanVar(value=config.REPROCESSAR_NAO)
        var_debug = tk.BooleanVar(value=config.DEBUG)

        def campo(rotulo, variavel, dica=""):
            nonlocal linha
            ttk.Label(quadro, text=rotulo).grid(row=linha, column=0, sticky="w", pady=4)
            entrada = ttk.Entry(quadro, textvariable=variavel, width=54, style="Campo.TEntry")
            entrada.grid(row=linha, column=1, columnspan=2, sticky="we", pady=4)
            if dica:
                linha += 1
                ttk.Label(quadro, text=dica, style="Dica.TLabel", wraplength=560).grid(
                    row=linha, column=1, columnspan=2, sticky="w"
                )
            linha += 1
            return entrada

        campo(
            "Endereço do portal:",
            var_url,
            "Obrigatório. Exemplo: https://portal.suaempresa.com.br",
        )
        campo(
            "Perfil de login (opcional):",
            var_perfil,
            "Apenas um lembrete na tela de login. Não é senha.",
        )

        ttk.Label(quadro, text="Chrome (opcional):").grid(row=linha, column=0, sticky="w", pady=4)
        ttk.Entry(quadro, textvariable=var_chrome, width=42, style="Campo.TEntry").grid(
            row=linha, column=1, sticky="we", pady=4
        )
        self._criar_botao(
            quadro, "Procurar...",
            lambda: self._procurar_chrome(var_chrome),
            compacto=True, largura=13,
        ).grid(row=linha, column=2, sticky="e", padx=(8, 0), pady=4)
        linha += 1
        ttk.Label(
            quadro,
            text="Deixe vazio para o programa encontrar o Chrome automaticamente.",
            style="Dica.TLabel",
        ).grid(row=linha, column=1, columnspan=2, sticky="w")
        linha += 1

        ttk.Label(quadro, text="Porta de depuração:").grid(row=linha, column=0, sticky="w", pady=4)
        ttk.Entry(quadro, textvariable=var_porta, width=12, style="Campo.TEntry").grid(
            row=linha, column=1, sticky="w", pady=4
        )
        linha += 1

        ttk.Label(quadro, text="Limite de clientes:").grid(row=linha, column=0, sticky="w", pady=4)
        ttk.Entry(quadro, textvariable=var_limite, width=12, style="Campo.TEntry").grid(
            row=linha, column=1, sticky="w", pady=4
        )
        linha += 1
        ttk.Label(
            quadro,
            text="Vazio processa todas as linhas. Use um número para testar com poucas linhas.",
            style="Dica.TLabel",
        ).grid(row=linha, column=1, columnspan=2, sticky="w")
        linha += 1

        ttk.Checkbutton(
            quadro,
            text="Reprocessar também as linhas marcadas NÃO",
            variable=var_reproc,
        ).grid(row=linha, column=0, columnspan=3, sticky="w", pady=(8, 0))
        linha += 1
        ttk.Checkbutton(
            quadro,
            text="Modo diagnóstico (mostra detalhes técnicos no log)",
            variable=var_debug,
        ).grid(row=linha, column=0, columnspan=3, sticky="w")
        linha += 1

        def fechar():
            try:
                janela.grab_release()
            except tk.TclError:
                pass
            janela.destroy()

        def salvar():
            url = var_url.get().strip().rstrip("/")
            ok, mensagem = config.validar_url_portal(url)
            if not ok:
                messagebox.showerror("Configuração", mensagem, parent=janela)
                return
            perfil = var_perfil.get().strip()
            chrome = var_chrome.get().strip()
            if chrome and not Path(chrome).is_file():
                messagebox.showerror(
                    "Configuração",
                    "O caminho do Chrome informado não existe.",
                    parent=janela,
                )
                return
            try:
                porta = int(var_porta.get().strip())
                if not (1 <= porta <= 65535):
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Configuração",
                    "A porta de depuração deve ser um número entre 1 e 65535.",
                    parent=janela,
                )
                return
            limite_texto = var_limite.get().strip()
            try:
                limite = int(limite_texto) if limite_texto else None
                if limite is not None and limite < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Configuração",
                    "O limite de clientes deve ser vazio ou um número maior que zero.",
                    parent=janela,
                )
                return

            try:
                config.salvar_config(
                    url_portal=url,
                    perfil_login=perfil,
                    chrome_exe=Path(chrome) if chrome else None,
                    porta_cdp=porta,
                    limite_clientes=limite,
                    reprocessar_nao=var_reproc.get(),
                    debug=var_debug.get(),
                )
                config.carregar_config()
            except (OSError, ValueError) as erro:
                messagebox.showerror("Configuração", f"Não consegui salvar: {erro}", parent=janela)
                return
            fechar()
            self._registrar("INFO", "Configurações atualizadas.")
            self._atualizar_botoes()
            self.var_instrucao.set(
                "Clique em Iniciar. O Chrome abrirá no portal; faça o login e depois "
                "clique em \"Já estou logado\"."
            )

        botoes = ttk.Frame(quadro)
        botoes.grid(row=linha, column=0, columnspan=3, sticky="e", pady=(14, 0))
        self._criar_botao(
            botoes, "Salvar", salvar, compacto=True, largura=16, nivel="primario"
        ).grid(row=0, column=0, padx=(0, 8))
        self._criar_botao(
            botoes, "Cancelar", fechar, compacto=True, largura=16
        ).grid(row=0, column=1)
        janela.protocol("WM_DELETE_WINDOW", fechar)

    def _procurar_chrome(self, variavel):
        caminho = filedialog.askopenfilename(
            parent=self.root,
            title="Escolha o chrome.exe",
            filetypes=[("Chrome", "chrome.exe"), ("Executáveis", "*.exe")],
        )
        if caminho:
            variavel.set(caminho)

    # --- Execução -----------------------------------------------------------
    def _iniciar(self):
        if self.worker is not None and self.worker.is_alive():
            return
        ok, mensagem = config.validar_url_portal(config.URL_PORTAL)
        if not ok:
            messagebox.showwarning("Configuração", mensagem, parent=self.root)
            self._configuracoes()
            return
        if not self.planilha or not self.destino:
            messagebox.showwarning(
                "Antes de iniciar",
                "Escolha a planilha e a pasta onde os DWG serão salvos.",
                parent=self.root,
            )
            return

        resultado = self._validar_selecao(mostrar=True)
        if resultado is None or not resultado.ok:
            return
        if resultado.pendentes == 0:
            messagebox.showinfo("Nada a fazer", resultado.mensagem, parent=self.root)
            return

        detalhe = (
            f"{resultado.pendentes} linha(s) pendente(s) e "
            f"{resultado.ja_preenchidas} já preenchida(s).\n"
            f"Pasta de destino: {self.destino}"
        )
        if not messagebox.askyesno(
            "Iniciar execução",
            detalhe + "\n\nDeseja começar?",
            parent=self.root,
        ):
            return

        self.resumo = Resumo()
        self.controle = Controle(
            self.resumo,
            historico_path=config.PASTA_LOGS / f"alteracoes-{time.strftime('%Y%m%d')}.csv",
        )
        self._logger = registro.configurar(self.controle, config.PASTA_LOGS)
        registro.redirecionar(self._logger)
        self._limpar_log()
        self.controle.set(
            estado="abrindo",
            total_geral=resultado.pendentes + resultado.ja_preenchidas,
            concluidos=resultado.ja_preenchidas,
            ja_preenchidas=resultado.ja_preenchidas,
        )
        self._registrar(
            "INFO",
            f"Iniciando: {resultado.pendentes} cliente(s) para analisar. "
            f"Pasta dos DWG: {self.destino}",
        )
        self._ultimo_estado = "abrindo"
        self._finalizar_pendente = False
        self.worker = threading.Thread(target=self._trabalhar, daemon=True)
        self.worker.start()
        self._atualizar_botoes()

    def _trabalhar(self):
        try:
            preparacao = preparar(
                self.planilha,
                self.destino,
                reprocessar_nao=config.REPROCESSAR_NAO,
                limite_clientes=config.LIMITE_CLIENTES,
            )
            self.controle.set(
                total_geral=preparacao.ja_preenchidas + len(preparacao.pendentes),
                concluidos=preparacao.ja_preenchidas,
                ja_preenchidas=preparacao.ja_preenchidas,
            )
            executar(preparacao, self.controle, self.resumo)
        except Exception as erro:
            print("Falha inesperada:\n" + traceback.format_exc())
            if self.controle is not None:
                self.controle.set(estado="erro", mensagem=str(erro), fim=time.time())

    def _ja_fiz_login(self):
        if self.controle is None:
            return
        self._registrar("INFO", "Login confirmado. Continuando...")
        self.controle.evt_iniciar.set()

    def _pausar(self):
        if self.controle is None:
            return
        self._registrar("AVISO", "Pausando... aguarde o item atual terminar.")
        self.controle.evt_pausar.set()

    def _retomar(self):
        if self.controle is None:
            return
        self._registrar("INFO", "Continuando a execução.")
        self.controle.evt_pausar.clear()

    def _parar(self):
        if self.controle is None:
            return
        self._registrar("AVISO", "Parando... o progresso será salvo na planilha.")
        self.controle.evt_parar.set()

    def _finalizar(self):
        estado = self.controle.get("estado") if self.controle else "ocioso"
        if self._finalizar_pendente:
            return
        if estado in apresentacao.ESTADOS_EM_EXECUCAO:
            if not messagebox.askyesno(
                "Finalizar",
                "A execução está em andamento. Deseja interromper e finalizar?",
                parent=self.root,
            ):
                return
            self._finalizar_pendente = True
            self._registrar("AVISO", "Interrompendo a execução para finalizar...")
            self.controle.evt_parar.set()
            self._atualizar_botoes()
            return
        self._reset()

    def _reset(self):
        if self.controle is not None:
            self._registrar("INFO", "Rodada encerrada. Você já pode começar outra.")
        self.controle = None
        self.resumo = None
        self.worker = None
        self._ultimo_estado = "ocioso"
        self._finalizar_pendente = False
        self.var_progresso.set("0 / 0")
        self.progresso["value"] = 0
        self.var_analise_foco.set("Aguardando o início")
        self.var_analise_detalhe.set('Escolha a planilha e clique em "Iniciar".')
        self.var_baixados.set("0 baixados")
        self.var_com_cad.set("0 com CAD")
        self.var_sem_cad.set("0 sem CAD")
        self.var_pulados.set("0 já existiam")
        self.var_erros.set("0 erros")
        self.lbl_status.configure(
            text=apresentacao.ROTULOS_ESTADO["ocioso"],
            bg=apresentacao.CORES_ESTADO["ocioso"],
        )
        self.var_instrucao.set(
            "Pronto para uma nova rodada. Escolha a planilha e clique em Iniciar."
        )
        self._atualizar_botoes("ocioso")

    # --- Atualização periódica da tela -------------------------------------
    def _atualizar(self):
        if self._fechando:
            return
        if self.controle is not None:
            snapshot = self.controle.snapshot()
            estado = snapshot["estado"]
            self._aplicar_snapshot(snapshot)
            if estado != self._ultimo_estado:
                self._ultimo_estado = estado
                self._ao_mudar_estado(estado, snapshot)
                if self._finalizar_pendente and estado in apresentacao.ESTADOS_ENCERRADOS:
                    self._reset()
        self.root.after(200, self._atualizar)

    def _aplicar_snapshot(self, snapshot):
        estado = snapshot["estado"]
        self.lbl_status.configure(
            text=apresentacao.ROTULOS_ESTADO.get(estado, estado),
            bg=apresentacao.CORES_ESTADO.get(estado, "#374151"),
        )
        self._atualizar_botoes(estado)

        total = snapshot["total_geral"]
        concluidos = snapshot["concluidos"]
        self.var_progresso.set(f"{concluidos} / {total}")
        self.progresso["value"] = min(100, concluidos / total * 100) if total else 0

        self.var_baixados.set(f"{snapshot['baixados']} baixados")
        self.var_com_cad.set(f"{snapshot['com_cad']} com CAD")
        self.var_sem_cad.set(f"{snapshot['sem_cad']} sem CAD")
        self.var_pulados.set(f"{snapshot['pulados']} já existiam")
        self.var_erros.set(f"{snapshot['erros']} erros")

        foco, detalhe = apresentacao.painel_em_analise(
            estado,
            cliente=snapshot["cliente_atual"],
            ordem=snapshot["ordem_atual"],
            solicitacao=snapshot["solicitacao_atual"],
            linha=snapshot["linha_atual"],
            mensagem=snapshot["mensagem"],
        )
        self.var_analise_foco.set(foco)
        self.var_analise_detalhe.set(detalhe)

        decorrido = snapshot["decorrido"]
        rodape = f"Tempo decorrido: {self._formatar_tempo(decorrido)}" if snapshot["inicio"] else ""
        feitos = concluidos - snapshot["ja_preenchidas"]
        if estado == "executando" and feitos >= 3 and total > concluidos:
            restante = decorrido / feitos * (total - concluidos)
            rodape += f" · Restante estimado: {self._formatar_tempo(restante)}"
        self.var_rodape.set(rodape)

        self._append_log(snapshot)

    @staticmethod
    def _formatar_tempo(segundos):
        segundos = max(0, round(segundos))
        horas, resto = divmod(segundos, 3600)
        minutos, seg = divmod(resto, 60)
        if horas:
            return f"{horas}h {minutos}min {seg}s"
        if minutos:
            return f"{minutos}min {seg}s"
        return f"{seg}s"

    def _append_log(self, snapshot):
        log_seq = snapshot["log_seq"]
        if log_seq < self._log_seq_visto:
            self._limpar_log()
        novas = [item for item in snapshot["log"] if item["seq"] > self._log_seq_visto]
        if not novas:
            return

        no_fim = self.log_text.yview()[1] >= 0.999
        self.log_text.configure(state="normal")
        for item in novas:
            linha, tag = apresentacao.formatar_linha_log(
                item["hora"], item["nivel"], item["texto"]
            )
            self.log_text.insert("end", linha, tag)
        self.log_text.configure(state="disabled")
        self._log_seq_visto = max(item["seq"] for item in novas)
        if no_fim:
            self.log_text.see("end")

    def _limpar_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._log_seq_visto = 0

    def _ao_mudar_estado(self, estado, snapshot):
        if self._finalizar_pendente and estado in apresentacao.ESTADOS_ENCERRADOS:
            return
        if estado == "sessao_caiu":
            messagebox.showwarning(
                "Sessão caiu",
                f"{snapshot['mensagem']}\n\n"
                "A execução foi interrompida e esse cliente ficou em branco na planilha.\n"
                "Faça login novamente no Chrome e clique em Iniciar para continuar de onde parou.",
                parent=self.root,
            )
        elif estado == "erro":
            messagebox.showerror(
                "Erro",
                snapshot["mensagem"] or "A execução terminou com erro.",
                parent=self.root,
            )
        elif estado == "finalizado":
            resumo = self.resumo.texto_curto() if self.resumo else ""
            messagebox.showinfo(
                "Execução finalizada",
                f"{resumo}\n\nConfira a planilha. Clique em Finalizar para liberar uma nova rodada.",
                parent=self.root,
            )
        elif estado == "parado":
            messagebox.showinfo(
                "Execução interrompida",
                "O progresso já foi salvo na planilha.\n\n"
                "Clique em Finalizar para liberar uma nova rodada.",
                parent=self.root,
            )
        if estado in apresentacao.ESTADOS_AGUARDANDO_FINALIZAR:
            # Iniciar fica desabilitado até Finalizar; a instrução do passo 2
            # não pode continuar dizendo "clique em Iniciar".
            self.var_instrucao.set(
                "Rodada encerrada. Clique em Finalizar para liberar uma nova rodada."
            )

    def _atualizar_botoes(self, estado=None):
        if estado is None:
            estado = self.controle.get("estado") if self.controle else "ocioso"
        habilitados = apresentacao.botoes_habilitados(
            estado, bool(self.planilha), bool(self.destino)
        )
        if not config.URL_PORTAL:
            habilitados["iniciar"] = False
        niveis = apresentacao.niveis_dos_botoes(estado)
        for nome, botao in self.botoes.items():
            if botao is None:
                continue
            nivel = niveis.get(nome, "secundario")
            habilitado = bool(habilitados.get(nome))
            # Só repinta o que mudou: _atualizar() roda várias vezes por segundo.
            if (getattr(botao, "_nivel", None) == nivel
                    and getattr(botao, "_habilitado", None) == habilitado):
                continue
            self._aplicar_aparencia(botao, nivel, habilitado)

    # --- Utilidades ---------------------------------------------------------
    def _registrar(self, nivel, mensagem):
        """Manda uma mensagem para o log da tela e para o arquivo."""
        if self._logger is not None:
            niveis = {
                "INFO": logging.INFO,
                "OK": logging.INFO,
                "AVISO": logging.WARNING,
                "ERRO": logging.ERROR,
            }
            self._logger.log(niveis.get(nivel, logging.INFO), mensagem)
        elif self.controle is not None:
            self.controle.registrar_log(nivel, mensagem)

    def _abrir_pasta_logs(self):
        try:
            config.PASTA_LOGS.mkdir(parents=True, exist_ok=True)
            self._abrir_pasta(config.PASTA_LOGS)
        except Exception as erro:
            messagebox.showerror("Logs", f"Não consegui abrir a pasta de logs: {erro}",
                                 parent=self.root)

    @staticmethod
    def _abrir_pasta(caminho):
        try:
            os.startfile(str(caminho))
        except Exception:
            pass

    def _ao_fechar(self):
        estado = self.controle.get("estado") if self.controle else "ocioso"
        if estado in apresentacao.ESTADOS_EM_EXECUCAO:
            if not messagebox.askyesno(
                "Sair",
                "A execução está em andamento. Deseja interromper e sair?",
                parent=self.root,
            ):
                return
            if self.controle is not None:
                self.controle.evt_parar.set()
            if self.worker is not None:
                self.worker.join(timeout=5)
        self._fechando = True
        self.root.destroy()


def iniciar():
    """Cria a janela e entra no loop principal."""
    root = tk.Tk()
    Aplicativo(root)
    root.mainloop()
