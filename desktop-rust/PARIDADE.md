# ArtFinder desktop em Rust

O inventário cobre o desktop anterior, com base em `templates/index.html`, `templates/viewer.js`, `app.py`, `artfinder/api/library.py` e `desktop.py`. A coluna Rust registra o que está implementado ou ainda precisa de trabalho. A distribuição Android segue como uma frente própria.

## Tecnologias avaliadas

| Tecnologia | Aplicação no ArtFinder | Custo da adoção |
|---|---|---|
| **egui + eframe**, em uso | Interface, estado e integrações em Rust. Permite redesenhar cartões, virtualizar a grade e manter o executável Windows já compilável. | Estilo e controles avançados de mídia dependem de implementação própria. A versão atual precisa de validação assistiva com AccessKit. [eframe](https://docs.rs/eframe/0.31.1/eframe/) |
| **Tauri 2 + HTML/CSS** | Backend Rust, interface na WebView do sistema. É a opção mais direta para aproveitar ideias e interações da interface anterior, incluindo vídeo embutido e semântica HTML. TypeScript pode entrar conforme a UI crescer. | Exige adaptar chamadas antigas para comandos Rust, definir a ponte e suas permissões e testar o empacotamento com WebView2 no Windows. [Arquitetura](https://v2.tauri.app/concept/architecture/) · [WebView](https://v2.tauri.app/reference/webview-versions/) · [Permissões](https://v2.tauri.app/security/capabilities/) |
| **Slint** | Interface declarativa compilada, com lógica em Rust e arquivos `.slint` próprios para composição e temas. | Exige reimplementar a grade, os formulários e o visualizador no modelo de componentes do Slint. [Linguagem](https://docs.slint.dev/latest/docs/slint/guide/language/concepts/slint-language/) |
| **Dioxus Desktop** | Componentes declarativos em Rust e estilos CSS, renderizados pela WebView. | Exige portar o estado da interface para componentes reativos e validar a integração de mídia e distribuição. [Desktop](https://dioxuslabs.com/learn/0.7/guides/platforms/desktop/) |

Esta revisão mantém egui e separa o desenho da grade e da navegação em `src/interface.rs`. Tauri é a primeira alternativa a prototipar se vídeo embutido e acessibilidade nativa via WebView se tornarem critérios de distribuição. SQLite, adaptadores de fontes e biblioteca continuam aproveitáveis em qualquer das opções.

## Direção visual

Uma barra lateral reúne **Explorar**, **Biblioteca** e **Aplicativo**. A busca tem o campo e o botão de destaque na primeira linha. Fontes, páginas e categorias ficam logo abaixo. Filtros detalhados abrem sob demanda, e os estados vazios indicam a próxima ação.

A grade dá prioridade à imagem. O cartão mostra artista primeiro e mantém fonte, classificação e resolução em um nível secundário. Guardar, baixar e revelar têm efeitos próprios. A versão para janelas estreitas troca a barra lateral por navegação superior. O fundo usa `#111117`, a navegação `#17161F`, os controles `#1E1D29`, o texto `#F4F1FA` e a ação primária `#B19BFC`. As instâncias estáticas de Manrope vêm da fonte inclusa no projeto, sob a [licença OFL](../android-native/licenses/MANROPE-OFL.txt).

## Inventário funcional

| Área | App anterior | Versão Rust |
|---|---|---|
| Busca | Busca unificada em Safebooru, Danbooru, Gelbooru, e621, Pixiv, Tumblr, Bluesky e DeviantArt. Seleção de fontes, categorias combinadas e 1–50 páginas por consulta. | As oito integrações, seleção de uma ou várias fontes, consultas livres separadas por ponto e vírgula e seleção de categorias na própria busca. |
| Resultados | Progresso, retorno parcial, cancelamento, avisos por fonte, páginas numeradas e contagem de artes. | Retorno por página, busca até o fim da fonte, cancelamento entre requisições, erros por fonte em Atividade, grade virtualizada com três tamanhos e continuação por cursor. Os resultados de busca ficam na sessão. |
| Organização da busca | Categorias por grupo, categoria de artista, favoritos, ordenação, seleção coletiva, filtro de categorias e categorias temporárias. | Favoritos, ordem, pesquisa por nome, grupo e tags, seleção de várias categorias e consulta livre. A interface de grupos e seleção coletiva difere da anterior. |
| Cadastro e tags | Criar, editar, apagar e reordenar categorias. Nome, emoji, cor, grupo, tags gerais e por fonte. Autocomplete e equivalências Pixiv/e621. | Edição dos metadados, importação, ordenação e equivalências Pixiv/e621. Sugestões da busca vêm das artes da biblioteca. A edição dos campos por fonte usa o seletor de configurações. |
| Filtros | Classificação (segura, sensível, adulta), tipo (imagem, GIF, WebP, vídeo), triagem, período, score mínimo, tags bloqueadas, ocultar baixadas, ordenação por score, recente, fonte e categoria. | Filtros de classificação, formato, data, pontuação, tags, texto e baixadas. Inclui orientação, resolução e cor. Resultado sem data fica fora de um período específico. |
| Privacidade | Proteção na grade e no visualizador, revelar uma arte sem abrir automaticamente, ocultar novamente e limpar revelações ao reativar proteção. Filtragem de arte marcada como IA. | Grade sem miniatura para conteúdo protegido, revelação em memória, ocultação explícita, proteção nos downloads e abertura do original. A navegação do visualizador pede revelação na grade. |
| Cartões | Ver a arte e a publicação, pesquisa reversa SauceNAO, procurar/favoritar/bloquear artista, ocultar publicação e guardar ou baixar separadamente. | Cartões maiores, publicação, SauceNAO, bloqueios, busca e favoritos de artista, coleções e ações individuais. |
| Visualizador e triagem | Visualização, anterior/próxima, zoom, arraste, roda, duplo clique, atalhos de triagem 1–4, Esc, imagem e vídeo embutido. | Imagem, GIF animado, zoom e reset, anterior/próxima e Esc. A triagem foi retirada. Vídeo salvo abre no player do sistema. Gestos de zoom e reprodução embutida seguem como lacunas. |
| Galeria | Baixadas, guardadas por URL e avaliadas; filtros por texto, fonte, categoria, classificação, tipo e coleção, ordenação, atualizar, remover, exportar e desmarcar avaliação. | Galeria com filtros para artes baixadas e guardadas e abas próprias. Navegação, filtros, atualização, exportação pelo caminho escolhido e remoção com confirmação. |
| Coleções | Criar, renomear, excluir, guardar com coleção, incluir ou retirar uma publicação em coleções múltiplas. | Criar, renomear e excluir, com vínculo pelo menu do cartão ou pelo visualizador. |
| Downloads | Ação individual, progresso, validação de formatos e tamanho, deduplicação, metadados, autor e link original. Exportação e acesso à pasta local. | Ação individual em segundo plano, estado por cartão, limite de tamanho, validação, SHA-256 para arquivos idênticos e hash de diferença para semelhantes. |
| Duplicatas | Busca de semelhantes, revisão com grupo de imagens e exclusão seletiva. | Aba com resultados semelhantes e remoção pelo visualizador. Agrupamento visual e comparação lado a lado seguem como lacunas. |
| Estatísticas e manutenção | Totais, uso de disco, triagem e distribuição por fonte/categoria, sincronizar registros, limpar índice, abrir pastas. | Tela de estatísticas para guardadas, baixadas e uso do disco, com distribuição dos downloads por fonte e categoria. Inclui reconciliação, limpeza confirmada e abertura de pastas. |
| Credenciais | Editar e remover credenciais, cofre do sistema, migração e limpeza do `.env` antigo. | Cofre do sistema, remoção e carregamento temporário do arquivo anterior. Migração persistente em lote com limpeza segura segue como lacuna. |
| Pareamento | Código local criptografado com validade, escolha de rede e seções, copiar código e enviar ou importar categorias e credenciais. | Criação, cópia e recepção de código, categorias e credenciais opcionais. Seleção de interfaces e opções por seção têm paridade parcial. |
| Idioma e dados | Português e inglês, preferências locais, armazenamento SQLite, perfil instalado e pacotes distribuíveis. | Interface principal em PT/EN e perfil Rust próprio. A importação lê o banco antigo e copia mídias. Parte das mensagens técnicas ainda aparece em português. |
| Integração | Servidor HTTP local com rotas de biblioteca, mídia e pareamento, modos desktop e Android, distribuições Windows/Linux/Android. | Binário desktop Windows. Compatibilidade com clientes HTTP da versão anterior, empacotamento Linux e integração final com Android permanecem como lacunas para a substituição completa. |

## Verificação da substituição

Antes de adotar o Rust como versão principal, validar o dia a dia com biblioteca importada, pareamento com o Android real, reprodução e zoom, acessibilidade por teclado e leitor de tela, e distribuição para as plataformas usadas. A importação já permite comparar os dois apps em perfis independentes.
