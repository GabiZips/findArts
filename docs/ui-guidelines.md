# ArtFinder: contrato de interface

Preservar o estilo existente. O redesenho visual anterior foi rejeitado; não
reintroduzir sua paleta, fontes ou extração de CSS sem aprovação. Melhorar
primeiro hierarquia, espaçamento, áreas clicáveis e previsibilidade.

## Artes e privacidade

- Uma ação tem um efeito: revelar, abrir, guardar, baixar e ocultar não se combinam.
- Na grade, tocar na área protegida revela apenas aquela arte; não abre o viewer.
- Depois de revelada, tocar abre. Um botão visível de ocultar permite protegê-la
  novamente, na grade e no viewer, sem depender de hover ou de duplo clique.
- Não usar multisseleção de artes, checkbox, Shift ou modo de seleção por toque longo.
- Guardar e baixar são ações individuais e visíveis; escolher coleções continua permitido.
- Cartões usam botões com texto Guardar/Baixar, sem botão redundante de ampliar.
- Ver na fonte, SauceNAO e remoções ficam no menu de opções; Escape e clique fora fecham o menu.
- Artista é o texto principal do rodapé; fonte, classificação e resolução ficam menores.
- Rolagem e arrasto não devem revelar conteúdo. Usar os controles/gestos nativos.
- Estado de revelação só vive na memória, identificado por fonte + ID. Não vai
  para configuração, conta, backup, saved instance state ou disco.
- Reativar a proteção global limpa todas as revelações. Proteger também vídeos
  e comparação; no Android, conteúdo oculto não é composto nem carregado.

## Legibilidade e acesso

- Alvos de 44 CSS px no web e 48 dp no Android; foco visível e ativação por teclado.
- Botões para ações, links para navegação. Sem botões aninhados.
- Manter português/inglês, semântica acessível e labels explícitos em sincronia.
- Evitar que controles cubram a arte ou exijam rolagem horizontal para descobri-los.
- Respeitar reduced motion e zoom. Não adicionar fontes remotas/frameworks para
  alterações meramente visuais.

## Validação

Testar em navegador real a 1440 e 390 px com formas geométricas sintéticas:
revelar, abrir, ocultar, selecionar, navegar, ordenar, reativar proteção e teclado.
Capturar e inspecionar screenshots. Compilar Android com Java 17/SDK 36 e separar
isso de testes de gestos em aparelho/emulador.

## Referências

Princípios adaptados, não cópias nem dependências instaladas:

- [Frontend design SKILL.md](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md): intenção visual e contenção.
- [Web interface guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md): foco, teclado, alvos de toque, responsividade.

Essas referências não criam vínculo com hospedagem ou serviços externos.
