"""Textos de ajuda exibidos dentro do aplicativo."""

BOAS_VINDAS = """Bem-vindo ao Downloader CAD.

Em três passos:
1. Escolha a planilha de controle (.xlsx) e a pasta onde os DWG serão salvos.
2. Clique em Iniciar e faça login no portal na janela do Chrome que abrir.
3. Volte ao aplicativo e clique em "Já estou logado".

O login é sempre manual: o programa não guarda senha.
Antes de começar, configure o endereço do portal."""


AJUDA = """COMO USAR O DOWNLOADER CAD

O QUE ELE FAZ
- Lê a planilha de controle e, para cada linha pendente, consulta o portal,
  baixa o DWG mais recente da solicitação e grava SIM ou NÃO na coluna CAD.
- Linhas com CAD já preenchido são puladas: rodar de novo continua de onde parou.
- Se a consulta falhar, a célula fica em branco para ser refeita depois.

ANTES DE COMEÇAR
- Tenha o Google Chrome instalado.
- Feche a planilha no Excel. Com ela aberta, o programa não consegue salvar.
- Escolha uma pasta de destino que já exista. O programa não cria a pasta raiz.
- A planilha precisa ser .xlsx e ter as colunas SOLICITACAO, Nome do cliente e CAD.

PASSO A PASSO
1. Clique em "Carregar planilha" e escolha o arquivo .xlsx.
2. Na sequência, escolha a pasta onde os DWG serão salvos.
3. Confira a mensagem de validação (pendentes e já preenchidas).
4. Clique em Iniciar. O Chrome abre na tela de login do portal.
5. Faça login e escolha o perfil de acesso, se aparecer.
6. Volte ao aplicativo e clique em "Já estou logado".
7. Acompanhe o progresso e o log. Em "Analisando agora" aparecem o cliente,
   a ordem, a solicitação e a linha da planilha que estão sendo consultados.
   Use Pausar, Retomar ou Parar quando precisar.
8. Ao terminar, clique em Finalizar para liberar uma nova rodada.

O QUE SIGNIFICA CAD
- SIM: foi encontrado e baixado pelo menos um DWG da solicitação.
- NÃO: a consulta funcionou, mas não há DWG.
- Em branco: a consulta falhou ou a sessão caiu. A linha será refeita.

PROBLEMAS COMUNS
- "A planilha parece estar aberta no Excel": feche o arquivo e tente de novo.
- "A sessão do portal caiu": faça login novamente no Chrome e inicie outra rodada.
- "Não encontrei o Google Chrome": instale o Chrome ou informe o caminho em
  Configurações.
- "A pasta de destino não existe": escolha uma pasta existente.

PRIVACIDADE
- O login é manual; nenhuma senha é salva.
- A planilha, os DWG e os logs ficam apenas na sua máquina.
- O programa não envia dados para nenhum lugar além do portal acessado."""


CONFIGURACAO = """CONFIGURAÇÕES

Endereço do portal
- Informe o endereço completo, começando com http:// ou https://.
- É salvo apenas neste computador.

Perfil de login (opcional)
- Apenas um lembrete na tela de login. Não é senha.

Chrome (opcional)
- Deixe vazio para o programa encontrar o Chrome automaticamente.

Porta de depuração
- Só mude se outra instalação já estiver usando a porta padrão (9222).

Limite de clientes
- Vazio processa todas as linhas. Um número serve para testar com poucas linhas.

Reprocessar NÃO
- Inclui novamente as linhas marcadas NÃO. Use com cuidado e confirme a quantidade."""
