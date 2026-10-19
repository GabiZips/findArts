# ADR 0009: cofre nativo para credenciais desktop

Status: integração desktop implementada no código; distribuição ainda pendente.
Data: 2026-10-18
Decisor: mantenedor, autorização nesta conversa.

## Contexto

Credenciais desktop são atualmente lidas de config.py e gravadas em .env
por app.py. Pareamento também depende dessas rotinas. Trocar apenas a escrita
causaria perda aparente de login no próximo início ou ressuscitaria valores
antigos durante remoção. A migração precisa cobrir o ciclo inteiro.

## Decisão

Usar um adaptador único para cofre nativo, com campos permitidos explicitamente.
Windows: keyring WinVaultKeyring; Linux: Secret Service; macOS: Keychain.
Não aceitar descoberta automática de backends de terceiros nem fallback para
texto puro. Cofre indisponível deve gerar erro seguro, sem expor a exceção original.
Isso não protege contra malware com acesso à sessão do usuário.

Configurações não secretas continuam separadas. Não alterar formatos de tags,
coleções ou pareamento nesta primeira etapa. Não adicionar conta ou servidor.

## Alternativas

- .env: simples e compatível, mas texto puro; somente compatibilidade legada.
- Arquivo cifrado por DPAPI: possível no Windows, mas exige formato próprio;
  preferir a interface de credenciais do sistema para segredos pequenos.
- Cofre com senha mestra: exige recuperação, bloqueio e UX adicionais;
  fora desta etapa. Não improvisar criptografia.

## Registro da primeira etapa (superado pela integração abaixo)

Concluído: utils/credential_store.py e oito testes sintéticos. O módulo não é
importado pelo app nem modifica credenciais reais. O keyring ainda não foi
adicionado aos locks: fazê-lo junto da integração e auditar as dependências.

Próxima etapa, antes de ativar:

1. Centralizar a allowlist hoje em app.py e testar inicialização, salvar,
   remover e pareamento pela mesma camada.
2. Definir precedência entre ambiente explícito, cofre e .env legado. Uma
   remoção não pode fazer uma credencial antiga reaparecer no próximo início.
3. Migração explícita, idempotente e retomável: conferir cada gravação por
   leitura, sem sobrescrever credenciais existentes diferentes silenciosamente.
4. Não apagar .env automaticamente. Só oferecer remoção dos campos migrados
   após confirmação; preservar outras configurações e explicar backups antigos.
5. Testar cofre bloqueado/ausente, falhas parciais, limites do backend,
   importação/rollback e reinício usando dados sintéticos.
6. Adicionar keyring aos locks, empacotar os backends e testar cofre real com
   identidade de teste separada. Não considerar mocks prova dessa integração.
7. Em seguida criar instalador Windows por usuário, mantendo dados separados
   dos binários e testando atualização/desinstalação.

## Limites da primeira etapa

A primeira etapa é deliberadamente inativa: o app continua funcionando como
antes, mas o .env ainda contém os segredos existentes. Escrita verificada no
adaptador não fornece transação entre vários campos. Falha pode ter alterado
um campo no cofre; a futura migração deve preservar a origem até confirmação.

## Integração realizada em 18/10/2026

- Allowlist centralizada em utils/credentials.py. Inicialização, configurações
  e pareamento usam o cofre nativo; novos valores não são escritos no .env.
- Registros JSON versionados por campo. Valor vazio é uma remoção explícita:
  impede recuperar o segredo legado após reinício. Não apagar esses registros
  por fora do app enquanto houver .env legado.
- Precedência: registro nativo > ambiente explícito > .env. O loader legado
  já dá prioridade ao ambiente. Se o cofre não puder ser lido ou estiver
  inválido, inicializar sem credenciais e indicar erro nas configurações.
- Namespace separado pelo caminho normalizado da pasta de dados. Mover essa
  pasta exige transferência explícita; não mover silenciosamente no instalador.
- Windows usa persistência local, não roaming enterprise. Linux/macOS ainda
  exigem validação real dos respectivos serviços de cofre.
- Migração acionada pelo botão nas configurações, com confirmação. Só copia
  campos ainda ausentes no cofre, verifica leitura e nunca remove .env.
  Cofre que falhou na inicialização exige desbloqueio e reinício antes disso.
- Atualização múltipla tem rollback por campo em falhas normais, mas não é
  transação resistente a queda do processo/energia. Erro de rollback exige
  reinício e revisão; nunca prometer migração concluída nesse caso.
- keyring incluído nos três locks; backend explícito incluído no spec.

Validação: 108 testes Python, Ruff e 15 testes JS passaram. Escrita/leitura/
exclusão no cofre real do Windows verificadas com namespace sintético, já limpo.
pip-audit não reportou vulnerabilidades conhecidas nos três locks atualizados.

## Próximo ponto de retomada

Atualização em 19/10/2026: limpeza opcional de .env implementada por confirmação.
Somente campos iguais ao valor verificado no cofre, ou explicitamente removidos
no cofre, são retirados; conflitos, comentários e outros dados são preservados.
Nenhum arquivo pessoal foi limpo na validação. Backups antigos não são alterados.

Multisseleção de artes foi removida do PC e Android por decisão do mantenedor.
Guardar, baixar e ocultar passam a ser ações individuais. Coleções e seleção de
fontes/tags continuam disponíveis.

Instalador por usuário preparado em packaging/windows/artfinder.iss e
scripts/build-windows-installer.ps1; ainda não compilado nem validado por falta
do compilador Inno Setup, cuja instalação foi bloqueada pela revisão automática.

1. Testar EXE empacotado e interação real do novo botão em navegador.
2. Implementar remoção opcional dos campos legados com confirmação e verificação;
   atualmente o .env antigo ainda contém os segredos e isso é informado na UI.
3. Melhorar identificação de origem por campo e recuperação de falha parcial.
4. Criar instalador por usuário sem alterar a pasta de dados; testar instalação
   limpa, atualização, desinstalação e preservação dos segredos no cofre.
5. Validar Linux com Secret Service e manter Android nativo fora dessa migração.
