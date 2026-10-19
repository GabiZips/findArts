# Preparação para publicação pública

Esta revisão não autoriza publicar o repositório nem promete segurança absoluta.
O repositório foi confirmado privado durante a revisão de 18/10/2026.

## Verificações realizadas

- Histórico de todas as referências locais, atualizado por fetch: Gitleaks
  8.30.1 com relatório completamente redigido em diretório ignorado.
  Três alertas revisados: duas constantes públicas do cliente Pixiv, também
  presentes em pixivpy3, e um falso positivo entre campos vazios de .env.example.
  Nenhuma credencial pessoal foi confirmada nesses alertas. Scanners têm limites.
- Locks Python de core, Windows e Linux atualizados e auditados com pip-audit:
  sem vulnerabilidades conhecidas reportadas nessa execução. Isso não cobre
  dependências Gradle, nem garante ausência de vulnerabilidades desconhecidas.
- Testes Python após atualização: 111 passaram; Ruff sem problemas (19/10/2026).
- Web: 13 testes Node passaram; verificações sintéticas do visualizador em
  Edge headless a 600 e 1440 px passaram. Não equivalem a revisão visual completa.
- Android: 23 testes unitários passaram, lintDebug concluiu e APK debug compilou
  com Java 17/SDK 36. Consultar o relatório de lint para avisos não bloqueantes.
- Interação de privacidade: estado temporário por fonte/ID, ocultação explícita,
  reset pela proteção global; vídeos web não iniciam automaticamente.

## Pendências antes de publicar uma release

- Testar instalação limpa e atualização no Windows e Android reais.
- Validar toque, abertura individual, arrasto, zoom, ocultação e rotação no Android;
  compilação e testes unitários não comprovam esses gestos.
- Inspecionar layouts com conteúdo sintético em navegador largo e estreito.
- Auditar dependências Android e repetir os scans na revisão exata a publicar.
- Inspecionar conteúdo dos pacotes, arquivos rastreados e histórico completo:
  excluir dados pessoais, cookies, .env, assinaturas e downloads.
- Revisar licença, documentação pública, permissões e limitações das fontes.
- Validar builds Linux e assinatura/versão dos pacotes de distribuição.
- Novas credenciais desktop usam cofre nativo. .env legado ainda pode conter
  segredos: migração e limpeza opcional exigem ação explícita nas configurações.
- Instalador Windows compilado e instalação inicial confirmada pelo usuário.
  Ciclo isolado de instalação/reinstalação/desinstalação validado. Atualização
  entre versões diferentes com dados reais ainda pendente.

## Próximas decisões

Contas não foram implementadas. A ADR 0008 é somente proposta: sincronização
opcional de tags e preferências primeiro, credenciais fora do escopo inicial.
Não incluir revelações de imagens em backups ou sincronização.

Preservar o estilo atual conforme ui-guidelines.md; melhorias visuais maiores
exigem aprovação, pois o redesenho anterior foi rejeitado pelo usuário.

## Candidata local Windows — 19/10/2026

- `dist/ArtFinder.exe`: 91.108.340 bytes; SHA-256
  `28b912d1ed41ae1f8352fae66c8e4d73c09fbd7aef29753d7f19f85540e6b68c`.
- Recursos da interface idênticos ao código atual, categorias iniciais vazias,
  nenhum caminho de dados pessoais identificado pelo verificador do pacote.
  A verificação por caminhos não detecta todo segredo possível.
- Inicialização e pareamento criptografado local passaram com diretório de dados
  temporário, sem abrir a interface e sem alterar configurações pessoais.
- `scripts/verify-windows-package.py` integra a geração do instalador e pode
  ser executado manualmente. Um pacote desatualizado interrompe a geração.
- Inno Setup 6.7.3 instalado pelo usuário. Em 19/10/2026, compilação concluída:
  `dist/review/ArtFinder-Setup-0.0.0-dev.exe` (92.161.610 bytes).
  A verificação do executável passou antes do empacotamento. Instalação inicial
  confirmada pelo usuário e hash do executável instalado conferido.
- Nenhum dispositivo Android conectado via ADB nesta etapa. Testes em aparelho,
  instalação limpa, atualização e desinstalação continuam pendentes.

### Teste isolado do instalador

Em 19/10/2026, o mesmo script Inno foi compilado com identidade separada
`ArtFinder.LocalInstallerCheck` e nome de teste. Foram validados:

- instalação sem privilégios administrativos em `build/review/installer-lifecycle`;
- hash do executável instalado idêntico ao pacote validado;
- reinstalação da mesma versão no mesmo destino;
- inicialização e pareamento com diretório de dados separado;
- desinstalação da cópia de teste e preservação do diretório de dados de teste;
- executável da instalação pessoal mantido com o mesmo hash.

O teste não cobre migração entre versões, credenciais reais, atalhos (desativados
no teste) nem Windows em outra máquina. A cópia instalada de teste foi removida.
