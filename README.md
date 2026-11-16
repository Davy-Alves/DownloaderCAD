# Downloader CAD

## Baixar

O executável está na página de releases:
**[DownloaderCAD-portable.zip](https://github.com/Davy-Alves/DownloaderCAD/releases/latest/download/DownloaderCAD-portable.zip)**

1. Baixe o `.zip` e **extraia** em uma pasta (não execute de dentro do zip).
2. Dê duplo clique em `DownloaderCAD.exe`. Não é preciso instalar Python.
3. Na primeira execução o Windows pode avisar que o aplicativo não é
   reconhecido — clique em **Mais informações** e **Executar assim mesmo**. O
   executável não é assinado digitalmente.

Requisitos: Windows e Google Chrome instalado. É preciso ter login no portal.

## Sobre o projeto

Eu precisava conferir, cliente por cliente, quais solicitações tinham desenho
CAD no portal e baixar o `.dwg` mais recente de cada uma. Era um trabalho
repetitivo — abrir a triagem, achar a solicitação, abrir o upload, escolher o
anexo e salvar na pasta certa — e fácil de errar. Escrevi este programa para
fazer essa parte sozinho e deixar o resultado na planilha.

O login continua sendo meu: o programa abre o Chrome na tela do portal e espera
eu entrar. Depois disso, ele percorre a planilha, consulta a triagem de cada
cliente, baixa os DWG e grava `SIM` ou `NÃO` na coluna `CAD`. Quando uma consulta
falha, a célula fica em branco para ser refeita na próxima rodada.

## Como funciona

1. Leio a planilha e separo as linhas com a coluna `CAD` vazia.
2. Abro o Chrome com um perfil dedicado e espero o login manual.
3. Para cada cliente, abro a triagem e extraio os números de solicitação.
4. Para cada solicitação, abro o upload e localizo os anexos `.dwg`.
5. Baixo só o arquivo mais recente e pulo o que já existe na pasta de destino.
6. Gravo `SIM` ou `NÃO` na planilha e salvo o arquivo a cada cliente.

Se a sessão do portal cair, a execução inteira para. Nesse caso, nem o cliente
atual nem os seguintes são marcados: a célula fica em branco para não registrar
`NÃO` por engano.

## O que o programa grava na coluna CAD

| Valor | Significado |
| --- | --- |
| `SIM` | Encontrei e baixei pelo menos um DWG da solicitação. |
| `NÃO` | A consulta funcionou, mas não há DWG. |
| em branco | A consulta falhou ou a sessão caiu. A linha será refeita na próxima rodada. |

Linhas com `CAD` já preenchido são puladas. Rodar de novo continua de onde
parou.

## Para usar o executável

1. Baixe e descompacte a pasta `DownloaderCAD`.
2. Dê duplo clique em `DownloaderCAD.exe`. Não é necessário instalar Python.
3. Em **Configurações**, informe o endereço do portal.
4. Clique em **Carregar planilha** e escolha o `.xlsx`.
5. Na sequência, escolha a pasta onde os DWG serão salvos. Ela precisa existir;
   o programa não cria a pasta raiz.
6. Clique em **Iniciar**. O Chrome abre no portal.
7. Faça login, escolha o perfil de acesso e volte ao aplicativo.
8. Clique em **Já estou logado**.
9. Use **Pausar**, **Retomar** ou **Parar** quando precisar.
10. Ao terminar, clique em **Finalizar** para liberar uma nova rodada. A janela
    e o Chrome continuam abertos.

Os botões **Como usar**, **Ver formato aceito** e **Baixar modelo de planilha**
ficam dentro da própria janela.

## Formato da planilha

- Arquivo `.xlsx`, primeira aba.
- Cabeçalho em qualquer uma das 20 primeiras linhas.
- Colunas obrigatórias: `SOLICITACAO`, `Nome do cliente` e `CAD`.
- Coluna opcional: `MUNICIPIO`.
- A coluna `CAD` deve começar vazia.
- Feche o arquivo no Excel antes de iniciar.

O botão **Baixar modelo de planilha** gera um arquivo pronto, com dados
fictícios e uma aba de instruções.

## Desenvolvimento

Requisitos: Python 3.11+ e Google Chrome.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

A lista de bibliotecas e versões que usei está em `docs/STACK.md`. A
configuração fica em `%LOCALAPPDATA%\DownloaderCAD\config.json`; o exemplo sem
valores é o `config.example.json`.

## Testes

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

Os testes usam dublês do Playwright e do portal, em `tests/fakes.py`, e não
abrem o site real. Eles também nunca tocam na planilha real nem na pasta de
destino: a fixture `ambiente_isolado` desvia tudo para uma pasta temporária.

Mudanças em seletores, URLs ou no fluxo de login/upload só podem ser validadas
rodando com o Chrome e o portal de verdade.

## Gerar o executável

```powershell
venv\Scripts\activate
pip install -r requirements-dev.txt
.\build_exe.ps1
```

O resultado fica em `dist\DownloaderCAD\` e em `dist\DownloaderCAD-portable.zip`.
A pasta `dist` não vai para o Git.

## Estrutura

```
main.py                  abre a janela
automacao/janela.py      interface Tkinter
automacao/controle.py    estado, eventos e log compartilhados
automacao/registro.py    log em arquivo
automacao/execucao.py    validação e orquestração
automacao/processador.py regra de negócio por cliente/solicitação
automacao/portal.py      Triagem, Upload e download no portal
automacao/navegador.py   Chrome real e espera do login
automacao/planilha.py    leitura/gravação da coluna CAD
automacao/formato.py     validação e modelo da planilha
automacao/config.py      configuração local
tests/                   testes com dublês
docs/                    decisões, guia do usuário e stack
```

## Decisões que tomei

**Login manual.** Não guardo senha nem tento automatizar o login. O programa
abre o Chrome e espera o clique em "Já estou logado". Isso evita credenciais no
código e não depende de seletores de uma tela que pode mudar.

**Sessão caída para tudo.** Se o portal derrubar a sessão, a rodada inteira para.
Continuar depois disso marcaria linhas erradas como `NÃO`.

**Erro deixa a célula em branco.** `NÃO` só significa "consultei e não havia
DWG". Timeout, erro de rede ou sessão caída não são a mesma coisa.

**A pasta de destino não é criada.** Se ela não existir, o programa aborta. Isso
evita gravar arquivos fora da pasta que eu uso para sincronizar.

**Só o DWG mais recente.** Cada solicitação pode ter vários anexos; baixar todos
só aumentaria a pasta sem necessidade.

**Tkinter em vez de painel web.** A interface faz parte da biblioteca padrão, não
adiciona dependência e não abre porta de rede. O usuário não precisa de terminal
nem de outro navegador.

**`Controle` separado da janela.** A automação roda em outra thread e não pode
tocar em Tkinter. O estado, a pausa e o log ficam em `automacao/controle.py`, o
que também permite testar esses comportamentos sem abrir uma janela.

**Configuração local.** Caminhos, URL do portal e perfil de login ficam em
`%LOCALAPPDATA%\DownloaderCAD\config.json`, não no repositório.

## O que aprendi

- Automação de portal real é frágil. Seletores, tempos de carregamento e sessão
  mudam, e a maior parte do trabalho é tratar esses casos, não o caminho feliz.
- Separá a regra de negócio da interface e do navegador foi o que tornou os
  testes possíveis sem abrir o site.
- Erro precisa fazer parte da regra: decidir quando deixar em branco é tão
  importante quanto decidir quando gravar `SIM` ou `NÃO`.
- Salvar a planilha a cada cliente protege o progresso, mas exige cuidado com a
  formatação do arquivo — por isso só regravo quando alguma linha mudou.
- Empacotar Playwright com PyInstaller exige coletar os arquivos do pacote
  explicitamente, o que está no `DownloaderCAD.spec`.

## Limitações

- Feito para Windows e Google Chrome.
- O executável não é assinado digitalmente; o Windows pode exibir um aviso de
  SmartScreen na primeira execução.
- O comportamento no portal real só pode ser validado manualmente.
- Não há CI nem lint configurados; a verificação é `python -m pytest`.

## Privacidade e segurança

- O login é manual e o programa não guarda senha.
- Planilhas, DWG, logs, configuração e perfil do Chrome estão no `.gitignore`.
- A configuração fica em `%LOCALAPPDATA%\DownloaderCAD\config.json`.
- O perfil do Chrome fica em `%LOCALAPPDATA%\DownloaderCAD\chrome-perfil`.
- Log da tela e arquivo: `%LOCALAPPDATA%\DownloaderCAD\logs\downloadercad.log`.
- Histórico de alterações: `%LOCALAPPDATA%\DownloaderCAD\logs\alteracoes-AAAAMMDD.csv`.
- Os logs podem conter nomes de clientes. Não os compartilhe sem necessidade.
- Use dados fictícios em exemplos, testes e capturas de tela.
