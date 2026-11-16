# Decisões do projeto

## 2026-11: log em linguagem simples e painel "Analisando agora"

**Decisão:** o painel de log deixa de mostrar o rótulo `INFO` (fica só a hora) e
mantém `OK`, `AVISO` e `ERRO` com cor. A linha do cliente vai em negrito, com um
marcador `»` que o render usa para reconhecê-la (`MARCA_DESTAQUE`). O painel
"Analisando agora" mostra o cliente em destaque e, abaixo, `Ordem 222 ·
Solicitação 1001 · linha 39 da planilha`. O `Controle` ganhou `ordem_atual` e
`solicitacao_atual`, preenchidos pelo `processador` apenas para exibição.

**Por quê:** quem opera a planilha não precisa saber o que é INFO, mas precisa
achar rapidamente de quem é a vez e qual solicitação está sendo consultada. O
`->` e o termo `Solicitud` saíram da tela; os detalhes técnicos (erros, caminhos)
continuam no log e no arquivo. A linha duplicada de "Planilha: CAD = ..." foi
removida: `registrar_alteracao` já registra a mudança uma vez.

## 2026-11: uma única aba do portal

**Decisão:** `garantir_chrome_aberto()` não passa mais a URL do portal na linha
de comando do Chrome. `abrir_sessao_portal()` reaproveita a aba em branco/nova
guia que o Chrome abriu e navega nela; só cria outra se não houver nenhuma.

**Por quê:** a URL no `Popen` abria uma aba e o `contexto.new_page()` + `goto`
abria uma segunda idêntica. Como o Chrome é aberto com perfil dedicado, a aba
inicial é previsível (nova guia), então reaproveitá-la é seguro.

## 2026-11: três níveis de botão e `tk.Button` no lugar do `ttk`

**Decisão:** os botões da janela seguem três níveis — primário (azul, a ação do
momento), secundário (branco com borda fina) e perigo (vermelho, encerra a
execução). Um único botão fica primário por estado (`niveis_dos_botoes`) e os
desabilitados usam fundo cinza claro e cursor `no`.

**Por quê:** o tema `vista` do ttk ignora cor de fundo em `TButton` — todo botão
vira o mesmo cinza com borda fina, sem hierarquia. `tk.Button` com `relief=flat`,
`bd=0` e `highlightthickness=1` permite cor sólida, hover próprio e um
desabilitado realmente apagado, sem dependência nova e mantendo o pacote do
PyInstaller do mesmo tamanho.

**Consequência:** não há cantos arredondados (Tk não desenha isso em widget) e
as alturas são obtidas por padding (40 px nas ações, 30 px nos compactos, 29 px
nos campos). Se o Windows do usuário não tiver Segoe UI, a altura varia 1–2 px.

A altura da janela vem de `altura_da_janela(altura_da_tela)`: o processo é
DPI-virtualizado (Tk enxerga 1536x864 numa tela 1920x1080 a 125%), então os
pixels já saem proporcionais, mas é preciso descontar a barra de título e a
barra de tarefas. Sem isso o rodapé do log ficava atrás da barra de tarefas.

## 2026-11: interface nativa com Tkinter

**Decisão:** substituir o painel HTTP local por uma janela Tkinter.

**Por quê:** o usuário não deve precisar de terminal, navegador extra ou edição
de `config.json`. Tkinter faz parte da biblioteca padrão, não adiciona
dependência e é empacotado pelo PyInstaller. O painel HTTP também abria uma
porta local que não é necessária para o uso desktop.

## 2026-11: `Controle` separado da interface

**Decisão:** o robô conversa com `automacao/controle.py`, que guarda estado,
eventos, log e histórico. A janela apenas lê `snapshot()`.

**Por quê:** a thread de automação não pode tocar em Tkinter. Separar também
permite testar pausa, parada e log sem abrir uma janela.

## 2026-11: configuração local, sem dados da empresa no código

**Decisão:** URL do portal, perfil de login e caminhos ficam em
`%LOCALAPPDATA%\DownloaderCAD\config.json`, editáveis pela janela. O repositório
público não contém nome de empresa, domínio interno nem perfil corporativo.

**Por quê:** o projeto pode virar portfólio e ser compartilhado sem expor
informações internas. A chave antiga `base_url` continua aceita na leitura.

## 2026-11: log em arquivo e histórico de alterações

**Decisão:** todo `print` é redirecionado para um logger que grava em
`%LOCALAPPDATA%\DownloaderCAD\logs\downloadercad.log`. Cada mudança de CAD também
é registrada em um CSV diário.

**Por quê:** o executável é windowed e não tem terminal. O usuário precisa
acompanhar o andamento e conferir o que foi alterado na planilha. Cookies e
senhas nunca são registrados.

## 2026-11: login manual

**Decisão:** o app abre o Chrome e espera o clique em "Já estou logado".

**Por quê:** evita armazenar credenciais e não depende de seletores do login,
que podem mudar. Também respeita a política de não contornar a proteção do
portal.

## 2026-11: termos proibidos fora do repositório

**Decisão:** o teste que procura dados da empresa lê a lista de um arquivo
local, `%LOCALAPPDATA%\DownloaderCAD\termos-locais`, fora do repositório. Sem
esse arquivo, o teste é marcado como `skip`.

**Por quê:** a lista literal no código faria o próprio teste publicar as
palavras que ele deveria esconder. E deixá-la na raiz do projeto, mesmo no
`.gitignore`, fazia com que ela entrasse em qualquer zip manual da pasta. A
verificação continua funcionando na máquina de quem tem o arquivo, e o
repositório público não expõe os termos.
