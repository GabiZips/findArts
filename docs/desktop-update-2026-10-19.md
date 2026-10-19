# Atualização local de 19/10/2026

Repositório confirmado privado. Nenhum push, publicação, commit ou mudança de
visibilidade realizado nesta etapa.

## Alterações

- Removida multisseleção de artes da busca, galeria e visualizador web.
  Removidos checkbox, Shift, barra em lote e comparação baseada em seleção.
- Guardar e baixar disponíveis individualmente no cartão e no visualizador.
  Ações do cartão ficam abaixo da imagem e não dependem de hover.
- Android sem modo de seleção, checkbox ou seleção por toque longo.
  Escolher fontes, tags e coleções continua permitido.
- Proteção NSFW preservada por arte: revelar, abrir e ocultar são ações distintas.
- Limpeza opcional do .env por confirmação, verificando o cofre antes de remover
  cada campo. Arquivos pessoais não foram limpos durante os testes.
- Fontes do instalador Windows por usuário e script de compilação preparados.
  Ainda falta gerar/testar o Setup: instalação do Inno Setup foi bloqueada pela
  revisão automática, sem motivo específico fornecido pela ferramenta.

## Verificação

- 111 testes Python, Ruff, 13 testes JS e 23 testes Android passaram.
- Android: testDebugUnitTest, lintDebug e assembleDebug concluíram; lint com
  zero erros e 53 avisos. Gestos em aparelho não foram validados nesta etapa.
- Navegador Edge com dados sintéticos: revelar sem abrir, guardar somente a
  arte atual, abrir pelo cartão, ocultar e ausência de controles de multisseleção.
- Novo dist/review/ArtFinder.exe gerado. Conteúdo da interface comparado byte
  a byte com os arquivos atuais, sem .env nem categorias pessoais no pacote.

O APK gerado é debug, não uma atualização de distribuição assinada com a chave
de release. O instalador .iss não foi compilado; não tratá-lo como instalador pronto.
