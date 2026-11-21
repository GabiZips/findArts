use std::cell::Cell;
thread_local! {static EN:Cell<bool>=const{Cell::new(false)};}
pub fn set(on: bool) {
    EN.set(on)
}
pub fn tr(s: &str) -> &str {
    if !EN.get() {
        return s;
    }
    match s {
        "Busca" => "Search",
        "Galeria" => "Gallery",
        "Favoritos" => "Favorites",
        "Coleções" => "Collections",
        "Duplicatas" => "Duplicates",
        "Configurações" => "Settings",
        "Buscar" => "Search",
        "Categorias" => "Categories",
        "Carregar mais" => "Load more",
        "Somente seguro" => "Safe content only",
        "Maior pontuação" => "Highest score",
        "Filtrar resultados" => "Filter results",
        "Dimensões e pontuação" => "Dimensions and score",
        "Largura mínima" => "Minimum width",
        "Altura mínima" => "Minimum height",
        "Pontuação mínima" => "Minimum score",
        "Baixar resultados visíveis" => "Download visible results",
        "Abrir arte" => "Open artwork",
        "Visualizador" => "Viewer",
        "Publicação original" => "Original post",
        "Baixar original" => "Download original",
        "Organizar e exportar" => "Organize and export",
        "Bloquear publicação" => "Block post",
        "Bloquear artista" => "Block artist",
        "Remover download da galeria" => "Remove download",
        "Exportar original" => "Export original",
        "Caminho completo para exportar" => "Full export path",
        "Todas" => "All",
        "Paisagem" => "Landscape",
        "Retrato" => "Portrait",
        "Quadrada" => "Square",
        "Favorito" => "Favorite",
        "Categorias e biblioteca" => "Categories and library",
        "Importar categorias do ArtFinder instalado" => {
            "Import categories from installed ArtFinder"
        }
        "Importar categorias do Windows" => "Import Windows categories",
        "Parear com outro dispositivo" => "Pair with another device",
        "Incluir credenciais na transferência" => "Include credentials in transfer",
        "Gerar código (5 minutos)" => "Generate code (5 minutes)",
        "Código de pareamento" => "Pairing code",
        "Receber configuração" => "Receive settings",
        "Aplicar configuração recebida" => "Apply received settings",
        "Nome" => "Name",
        "Tags da busca" => "Search tags",
        "Salvar" => "Save",
        "Editar" => "Edit",
        "Remover" => "Remove",
        "Credenciais" => "Credentials",
        "Usar credenciais do arquivo .env do ArtFinder nesta sessão" => {
            "Use credentials from the installed ArtFinder .env for this session"
        }
        "Salvar no cofre do sistema" => "Save to system vault",
        "Tags ou categoria" => "Tags or category",
        "Tags bloqueadas" => "Blocked tags",
        "Artistas bloqueados" => "Blocked artists",
        "Publicações bloqueadas" => "Blocked posts",
        "Reproduzir vídeo" => "Play video",
        "Vídeo · salve o original para reproduzir" => "Save the original video to play it",
        "Filtrar por cor" => "Filter by color",
        "Tolerância" => "Tolerance",
        "Sugestões" => "Suggestions",
        "Remover do cofre" => "Remove from vault",
        "Favoritar categoria" => "Favorite category",
        "Restaurar índice da galeria" => "Reconcile gallery index",
        "Idioma" => "Language",
        "Explorar" => "Explore",
        "Biblioteca" => "Library",
        "Aplicativo" => "Application",
        "Buscar artes" => "Find artwork",
        "Digite uma tag ou categoria" => "Enter a tag or category",
        "Todas as fontes" => "All sources",
        "Selecionadas" => "Selected sources",
        "Fontes" => "Sources",
        "Páginas " => "Pages ",
        "Cancelar busca" => "Cancel search",
        "Filtrar categorias" => "Filter categories",
        "Gerenciar categorias" => "Manage categories",
        "Filtros" => "Filters",
        "Proteger conteúdo sensível" => "Protect sensitive content",
        "Ocultar da galeria" => "Hide downloaded artwork",
        "Classificação" => "Content rating",
        "Seguro" => "Safe",
        "Sensível" => "Sensitive",
        "Adulto" => "Adult",
        "Imagem" => "Image",
        "Vídeo" => "Video",
        "Qualquer data" => "Any date",
        "dias" => "days",
        "Qualquer orientação" => "Any orientation",
        "Largura ≥ " => "Width ≥ ",
        "Altura ≥ " => "Height ≥ ",
        "Pontuação ≥ " => "Score ≥ ",
        "Restaurar filtros" => "Reset filters",
        "Buscando artes" => "Searching for artwork",
        "Os resultados aparecem conforme cada fonte responde." => {
            "Results appear as each source responds."
        }
        "O que você quer encontrar?" => "What are you looking for?",
        "Digite uma tag ou selecione suas categorias para começar." => {
            "Enter a tag or select your categories to get started."
        }
        "Nenhuma arte com esses filtros" => "No artwork matches these filters",
        "Altere os filtros ou limpe o campo de busca nesta página." => {
            "Change the filters or clear the filter text on this page."
        }
        "Nenhuma arte guardada" => "No saved artwork",
        "Use Guardar em uma arte para encontrá-la aqui." => {
            "Use Save on an artwork to find it here."
        }
        "Sua galeria está vazia" => "Your gallery is empty",
        "Baixe uma arte para acessá-la neste dispositivo." => {
            "Download artwork to access it on this device."
        }
        "Nenhuma arte nesta coleção" => "This collection is empty",
        "Adicione artes a uma coleção pelo menu da publicação." => {
            "Add artwork to a collection from the artwork menu."
        }
        "Nenhuma duplicata encontrada" => "No duplicates found",
        "Imagens baixadas com conteúdo semelhante aparecem aqui." => {
            "Similar downloaded images appear here."
        }
        "Nenhum resultado" => "No results",
        "Confira as tags e abra Atividade para ver a resposta de cada fonte." => {
            "Check your tags and open Activity to see how each source responded."
        }
        "Ir para a busca" => "Go to search",
        "Mostrar imagem" => "Show image",
        "Abrir original" => "Open original",
        "Artista desconhecido" => "Unknown artist",
        "Guardado" => "Saved",
        "Guardar" => "Save",
        "Baixar" => "Download",
        "Baixado" => "Downloaded",
        "Baixando…" => "Downloading…",
        "Ocultar imagem" => "Hide image",
        "Estatísticas" => "Statistics",
        "Menor pontuação" => "Lowest score",
        "Em alta" => "Trending",
        "Fonte" => "Source",
        "Categoria" => "Category",
        "Ordem de chegada" => "Arrival order",
        "Atualizar" => "Refresh",
        "arte" => "artwork",
        "artes" => "artworks",
        "Buscando nas fontes" => "Searching sources",
        "Abrindo original" => "Opening original",
        "Atividade" => "Activity",
        "Analisando cores" => "Analyzing colors",
        "Escolher coleção" => "Choose collection",
        "Nova coleção" => "New collection",
        "Criar coleção" => "Create collection",
        "Renomear coleção" => "Rename collection",
        "Novo nome" => "New name",
        "Renomear" => "Rename",
        "Estatísticas indisponíveis" => "Statistics unavailable",
        "Guardadas" => "Saved",
        "Baixadas" => "Downloaded",
        "No disco" => "On disk",
        "Por fonte" => "By source",
        "Por categoria" => "By category",
        "Sem categoria" => "Uncategorized",
        "Original baixado" => "Original downloaded",
        "← Anterior" => "← Previous",
        "Próxima →" => "Next →",
        "Revele a próxima arte protegida na grade para abrir." => {
            "Reveal the next protected artwork in the grid before opening it."
        }
        "Apagar este arquivo da galeria?" => "Delete this file from the gallery?",
        "Confirmar remoção" => "Confirm removal",
        "Cancelar" => "Cancel",
        "Buscar artista" => "Search for artist",
        "Favoritar artista" => "Favorite artist",
        "Artistas" => "Artists",
        "Nome exibido" => "Display name",
        "Grupo" => "Group",
        "Cor" => "Color",
        "Ícone" => "Icon",
        "Excluir coleção" => "Delete collection",
        "Confirme a exclusão da coleção. As artes continuam na biblioteca." => {
            "Confirm collection deletion. Artwork stays in your library."
        }
        "Importação e manutenção" => "Import and maintenance",
        "Dispositivos" => "Devices",
        "Preferências" => "Preferences",
        "Grupos" => "Groups",
        "Limpar categorias selecionadas" => "Clear selected categories",
        "Copiar código" => "Copy code",
        "Páginas por consulta" => "Pages per query",
        "Até o fim" => "Until the end",
        "Continua até a fonte ficar sem páginas ou você cancelar." => {
            "Continue until the source runs out of pages or you cancel."
        }
        "página consultada" => "page fetched",
        "páginas consultadas" => "pages fetched",
        "Tamanho das imagens" => "Image size",
        "Compacta" => "Compact",
        "Grande" => "Large",
        "Uma por linha" => "One per row",
        _ => s,
    }
}
