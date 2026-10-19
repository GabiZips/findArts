# Candidata privada 0.10.1

Esta versão reúne as melhorias locais de privacidade, ações individuais,
pareamento, cofre de credenciais e empacotamento. Não autoriza publicação.

## Atualização Windows

Feche o ArtFinder e execute `dist/review/ArtFinder-Setup-0.10.1.exe`.
O AppId e o diretório de instalação são os mesmos do instalador anterior.
Os dados permanecem em `%LOCALAPPDATA%\ArtFinder`; o instalador só distribui
o executável. Não desinstale antes de atualizar.

## Atualização Android

O APK de distribuição usa `io.github.gabizips.artfinder`, versão 0.10.1,
versionCode 100001 e a chave de distribuição original. O Preview usa
`io.github.gabizips.artfinder.debug` e a chave debug local. Cada canal atualiza
somente seu próprio app e mantém seu próprio armazenamento.

- App normal: `dist/review/ArtFinder-Android-0.10.1.apk`.
- Preview: `dist/review/ArtFinder-Preview-0.10.1.apk`.

Instale sobre o app correspondente, sem desinstalar. Se o Android indicar
conflito de assinatura, pare: desinstalar pode apagar dados. Dados adicionados
ao Preview não migram automaticamente para o app normal.

## Confirmação de preservação

Antes da atualização, anote a quantidade de tags e coleções, uma configuração
alterada e uma arte guardada. Após atualizar, confira esses itens, autenticação
das fontes, abertura das artes e arquivos já baixados. Não compartilhe senhas
ou códigos de pareamento para reportar o resultado.

O usuário confirmou os fluxos do Preview anterior no celular. Atualização
entre versões com dados reais ainda depende dessa confirmação após instalar
0.10.1. Não confundir build/testes passando com migração validada em aparelho.

## Verificações locais

- 111 testes Python e 13 testes JavaScript passaram; Ruff sem erros.
- 23 testes Android passaram; lint, assembleDebug e assembleRelease concluídos.
- APK release assinado e verificado com o certificado original documentado em
  android-signing.md; identificador e versionCode 100001 conferidos no pacote.
- Gitleaks nos arquivos preparados para commit não apontou segredos.
- Repositório confirmado privado; commits locais, sem push nem tags de release.
- Instalador Windows 0.10.1 compilado com os mesmos recursos já validados.
