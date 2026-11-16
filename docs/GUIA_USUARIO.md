# Guia rápido do usuário

## Antes de começar

- Google Chrome instalado.
- A planilha de controle em `.xlsx`, fechada no Excel.
- Uma pasta existente para receber os DWG.
- Acesso ao portal (o login é feito por você, no Chrome).

## Primeiro uso

1. Abra `DownloaderCAD.exe`.
2. Em **Configurações**, informe o endereço do portal.
3. Se quiser, informe o texto do perfil de login e o caminho do Chrome.
4. Salve.

## Cada execução

1. Clique em **Carregar planilha** e escolha o `.xlsx`.
2. Na sequência, escolha a pasta onde os DWG serão salvos.
3. Confira a mensagem de validação.
4. Clique em **Iniciar**.
5. No Chrome, faça login e escolha o perfil de acesso.
6. Volte ao aplicativo e clique em **Já estou logado**.
7. Acompanhe o progresso e o log. Em **Analisando agora** aparecem o cliente,
   a ordem, a solicitação e a linha da planilha em consulta.

## Botões

- **Pausar / Retomar**: interrompe e continua entre um cliente e outro.
- **Parar**: interrompe a rodada e mantém o resultado na tela.
- **Finalizar**: encerra a rodada e libera uma nova planilha. Não fecha a janela.

## Planilha aceita

Colunas obrigatórias:

- `SOLICITACAO`
- `Nome do cliente`
- `CAD`

Coluna opcional: `MUNICIPIO`.

A coluna `CAD` começa vazia. O programa grava `SIM` ou `NÃO`. Se a consulta
falhar, a célula fica em branco para a próxima rodada.

Use **Baixar modelo de planilha** para gerar um exemplo pronto.

## Onde ficam os arquivos

- Configuração: `%LOCALAPPDATA%\DownloaderCAD\config.json`
- Log: `%LOCALAPPDATA%\DownloaderCAD\logs\downloadercad.log`
- Histórico de alterações: `%LOCALAPPDATA%\DownloaderCAD\logs\alteracoes-AAAAMMDD.csv`

## Problemas comuns

| Mensagem | O que fazer |
| --- | --- |
| Planilha aberta no Excel | Feche o arquivo e inicie de novo. |
| Pasta de destino não existe | Escolha uma pasta que já exista. |
| Sessão caiu | Faça login novamente no Chrome e clique em Iniciar. |
| Chrome não abriu | Instale o Chrome ou informe o caminho em Configurações. |
| SmartScreen do Windows | Clique em "Mais informações" e "Executar assim mesmo". |

## Privacidade

- Nenhuma senha é salva.
- Planilha, DWG e logs ficam apenas na sua máquina.
- Os logs podem conter nomes de clientes; evite compartilhá-los.
