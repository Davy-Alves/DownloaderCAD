# Stack do projeto

Relatório do que o projeto realmente usa, lido do ambiente de desenvolvimento
(`venv`), do `requirements.txt`, do `pytest.ini` e dos arquivos de build.

## Linguagem

| Item | Versão |
| --- | --- |
| Python | 3.13.14 |
| Tkinter / Tcl-Tk | 8.6 (biblioteca padrão) |

O `requirements.txt` não fixa versões. A versão mínima real é **Python 3.11**,
exigida pelo pandas 3.1.1.

## Bibliotecas principais

| Biblioteca | Versão instalada | Para que serve |
| --- | --- | --- |
| pandas | 3.1.1 | Ler a planilha e localizar as linhas pendentes |
| openpyxl | 3.1.5 | Gravar a coluna `CAD` sem perder o restante da planilha; gerar o modelo |
| Playwright | 1.64.1 | Controlar o Chrome já aberto via CDP (Triagem, Upload e download) |
| pytest | 9.2.0 | Testes automatizados (desenvolvimento) |
| PyInstaller | 6.22.3 | Gerar o executável do Windows (desenvolvimento) |

Dependências transitivas relevantes: numpy 2.5.4 (pandas), greenlet 3.5.6 e pyee
14.0.0 (Playwright).

## Interface

Tkinter com `ttk` para os campos e `tk.Button` para os botões. A janela roda na
thread principal; a automação roda em outra thread e conversa com a tela pelo
módulo `automacao/controle.py`.

## Dados

Não há banco de dados, ORM ou serviço externo de persistência.

| Dado | Formato | Onde fica |
| --- | --- | --- |
| Planilha de controle | `.xlsx` | Escolhida pelo usuário a cada rodada |
| Histórico de alterações | `.csv` diário | `%LOCALAPPDATA%\DownloaderCAD\logs` |
| Log da aplicação | texto | `%LOCALAPPDATA%\DownloaderCAD\logs\downloadercad.log` |
| Configuração | `.json` | `%LOCALAPPDATA%\DownloaderCAD\config.json` |
| Perfil do Chrome | pasta do Chrome | `%LOCALAPPDATA%\DownloaderCAD\chrome-perfil` |

## Build, teste e qualidade

| Ferramenta | Situação |
| --- | --- |
| Build | PyInstaller, via `DownloaderCAD.spec` e `build_exe.ps1` |
| Testes | pytest, configurado em `pytest.ini` (`pythonpath = .`, `testpaths = tests`) |
| Lint | nenhum configurado |
| Formatter | nenhum configurado |
| Type checker | nenhum configurado |
| CI | nenhum (`.github/workflows` não existe) |
| Gerenciador de pacotes | pip + `requirements.txt` / `requirements-dev.txt` (sem versões fixas) |

## Infraestrutura e distribuição

- Aplicativo desktop para **Windows**, sem servidor, container ou deploy em nuvem.
- Usa o **Google Chrome instalado na máquina**, aberto com
  `--remote-debugging-port=9222` e um perfil dedicado.
- O portal é acessado pela URL configurada localmente; o login é manual.
- Distribuição: pasta `dist\DownloaderCAD\` com `DownloaderCAD.exe` e um
  `DownloaderCAD-portable.zip`. O executável não é assinado digitalmente.

## Arquitetura

Fluxo principal:

```
main.py
  └── janela.py (Tkinter)
        ├── controle.py      estado, pausa/parada, log e eventos
        ├── execucao.py      valida a rodada e orquestra
        │     └── processador.py   regra por cliente/solicitação
        │           ├── portal.py      Triagem, Upload e links de DWG
        │           └── navegador.py   Chrome/CDP, login e abas
        ├── planilha.py      leitura e gravação da coluna CAD
        ├── formato.py       validação da planilha e geração do modelo
        ├── registro.py      log em arquivo (redireciona stdout)
        └── config.py        configuração local
```

| Módulo | Responsabilidade |
| --- | --- |
| `main.py` | Abre a janela e registra falhas de inicialização |
| `automacao/janela.py` | Interface, botões, configurações e atualização periódica |
| `automacao/controle.py` | Estado compartilhado, pausa/parada e log da tela |
| `automacao/execucao.py` | Validação, preparação e ciclo da rodada |
| `automacao/processador.py` | Regra de negócio por cliente e por solicitação |
| `automacao/portal.py` | Interação com as telas do portal |
| `automacao/navegador.py` | Chrome, CDP, espera do login e abas |
| `automacao/planilha.py` | Leitura da planilha e gravação de `SIM`/`NÃO` |
| `automacao/formato.py` | Validação do arquivo e geração do modelo |
| `automacao/registro.py` | Log em arquivo e redirecionamento do `print` |
| `automacao/config.py` | Configuração local e validação da URL |
| `automacao/apresentacao.py` | Cores, fontes, textos e alturas da interface |
| `automacao/textos.py` | Textos de ajuda exibidos na janela |
| `automacao/resumo.py` | Resumo final da rodada |
| `automacao/alertas.py` | Bipe e aviso de sessão caída |
| `automacao/utils.py` | Sanitização de nomes de pasta |
| `automacao/excecoes.py` | `SessaoExpirada` e `Interrompido` |
| `tests/` | Testes com dublês; não acessam o portal real |

## Estrutura de pastas

```
main.py
automacao/
  janela.py, controle.py, execucao.py, processador.py
  portal.py, navegador.py
  planilha.py, formato.py
  config.py, registro.py
  apresentacao.py, textos.py, resumo.py, alertas.py, utils.py, excecoes.py
tests/
  conftest.py, fakes.py
  test_*.py
docs/
  decisions.md, GUIA_USUARIO.md, STACK.md
modelo/
  modelo_planilha.xlsx
config.example.json
requirements.txt, requirements-dev.txt
pytest.ini
build_exe.ps1, DownloaderCAD.spec, version_info.txt
LICENSE, README.md
```

## O que o projeto não tem

- Banco de dados, migrations ou ORM
- API HTTP ou frontend web
- Docker, Kubernetes ou deploy em nuvem
- Fila, cache ou serviço de mensageria
- Autenticação própria: o login é feito pelo usuário no Chrome
- Lint, formatter, type checker ou pipeline de CI configurados
