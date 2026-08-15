(() => {
  "use strict";

  const STORAGE_KEY = "artfinder.language";
  const SUPPORTED = new Set(["pt-BR", "en"]);

  // Portuguese is the source language used by the existing UI. Keeping the
  // dictionary in one file lets every desktop/mobile package share it.
  const EN = {
    "Navegação principal": "Main navigation",
    "Buscar": "Search",
    "Galeria": "Gallery",
    "Ativa/Desativa o efeito de blur global em imagens NSFW": "Enable or disable the global blur effect on NSFW images",
    "Banco:": "Database:",
    "imgs": "images",
    "imgs ·": "images ·",
    "Cancelar": "Cancel",
    "Busca": "Search",
    "Filtros": "Filters",
    "Conteúdo": "Content",
    "Todos": "All",
    "Sel.": "Select",
    "Outros": "Other",
    "Shipps": "Ships",
    "Selecionar/limpar tudo": "Select/clear all",
    "🔍 Buscar conteúdo...": "🔍 Search content...",
    "🎨 Artistas": "🎨 Artists",
    "Selecionar/limpar todos os artistas": "Select/clear all artists",
    "🔍 Filtrar artistas...": "🔍 Filter artists...",
    "Gerenciar categorias": "Manage categories",
    "Fontes": "Sources",
    "Carregando...": "Loading...",
    "Páginas por fonte": "Pages per source",
    "≈ 20 posts por fonte": "≈ 20 posts per source",
    "Estes filtros aplicam": "These filters apply",
    "na hora": "instantly",
    "sobre os resultados — sem precisar buscar de novo.": "to the results — no need to search again.",
    "Avaliação": "Review",
    "Não avaliadas": "Not reviewed",
    "Usar": "Use",
    "Talvez": "Maybe",
    "Rever depois": "Review later",
    "Não gostei": "Dislike",
    "Classificação": "Rating",
    "Sensível": "Sensitive",
    "Tipo de mídia": "Media type",
    "🖼️ Imagem": "🖼️ Image",
    "▶️ Vídeo": "▶️ Video",
    "Blacklist de Tags": "Tag blacklist",
    "Tags separadas por vírgula — excluídas dos resultados": "Comma-separated tags — excluded from results",
    "Score mínimo": "Minimum score",
    "Período": "Period",
    "7 dias": "7 days",
    "30 dias": "30 days",
    "3 meses": "3 months",
    "6 meses": "6 months",
    "1 ano": "1 year",
    "Buscando...": "Searching...",
    "Mostrar ou esconder o painel de busca": "Show or hide the search panel",
    "Mostrar/esconder painel lateral": "Show/hide sidebar",
    "Painel": "Panel",
    "Sel. Tudo": "Select all",
    "Desmarcar": "Clear selection",
    "👁️ Ocultar da galeria": "👁️ Hide gallery items",
    "sel. /": "selected /",
    "pág": "page",
    "Selecione 2 a 4 imagens para comparar lado a lado": "Select 2 to 4 images to compare side by side",
    "⧉ Comparar": "⧉ Compare",
    "Exportar URLs selecionadas como .txt": "Export selected URLs as .txt",
    "📋 Exportar URLs": "📋 Export URLs",
    "✨ Em Alta": "✨ Trending",
    "Por fonte": "By source",
    "Por categoria": "By category",
    "Guardar URL sem baixar (aparece na Galeria do ArtFinder)": "Save URL without downloading (shown in ArtFinder Gallery)",
    "📌 Guardar": "📌 Save",
    "⬇ Baixar": "⬇ Download",
    "Configure os filtros e clique em": "Configure the filters and click",
    "Os botões de página serão gerados aqui": "Page buttons will be generated here",
    "imagens": "images",
    "🔍 artista, fonte, tags...": "🔍 artist, source, tags...",
    "📅 Mais recentes": "📅 Newest",
    "📐 Resolução ↓": "📐 Resolution ↓",
    "Qualquer res.": "Any resolution",
    "🔄 Atualizar": "🔄 Refresh",
    "☑️ Selecionar": "☑️ Select",
    "🧬 Duplicatas": "🧬 Duplicates",
    "selecionada(s)": "selected",
    "Selecionar tudo": "Select all",
    "Limpar": "Clear",
    "🚫 Ocultar": "🚫 Hide",
    "📱 Salvar no celular": "📱 Save to phone",
    "🗑 Apagar do dispositivo": "🗑 Delete from device",
    "Tipo:": "Type:",
    "Ver:": "View:",
    "⬇ Baixados (Disco)": "⬇ Downloaded (Disk)",
    "📌 Guardados (Só URL)": "📌 Saved (URL only)",
    "Artes avaliadas na triagem que não foram baixadas nem guardadas": "Reviewed artwork which was neither downloaded nor saved",
    "★ Avaliadas": "★ Reviewed",
    "Filtrar pela pilha de triagem": "Filter by review group",
    "Pilha: todas": "Group: all",
    "Sem avaliação": "Not reviewed",
    "Todas": "All",
    "Clique em": "Click",
    "Atualizar": "Refresh",
    "para carregar": "to load",
    "Nenhuma imagem encontrada.": "No images found.",
    "Total no banco": "Total in database",
    "imagens únicas": "unique images",
    "Espaço no disco": "Disk usage",
    "MB em downloads/": "MB in downloads/",
    "Triagem": "Review",
    "escolhidas": "selected",
    "em dúvida": "undecided",
    "adiadas": "postponed",
    "descartadas (reversível)": "discarded (reversible)",
    "Manutenção": "Maintenance",
    "Sincronizar banco com o disco": "Sync database with disk",
    "Se você apagou imagens manualmente da pasta downloads/, o banco ainda acha que elas existem. Isto remove esses registros órfãos.": "If you manually deleted images from downloads/, the database still thinks they exist. This removes those orphaned records.",
    "Sincronizar": "Sync",
    "Limpar registro de downloads": "Clear download history",
    "Zera o histórico de downloads no banco —": "Clears the download history in the database —",
    "nenhum arquivo é apagado": "no files are deleted",
    "Serve para permitir baixar tudo de novo (o app deixa de pular imagens \"já baixadas\").": "This allows everything to be downloaded again (the app stops skipping previously downloaded images).",
    ". Serve para permitir baixar tudo de novo (o app deixa de pular imagens \"já baixadas\").": ". This allows everything to be downloaded again (the app stops skipping previously downloaded images).",
    "Pastas do aplicativo": "Application folders",
    "Abra as imagens baixadas ou a pasta onde ficam o .env, as categorias e o banco.": "Open downloaded images or the folder containing .env, categories and the database.",
    "Configuração": "Configuration",
    "Fontes e credenciais": "Sources and credentials",
    "Ative Pixiv, Tumblr, Bluesky, DeviantArt e outras fontes sem editar o arquivo .env.": "Enable Pixiv, Tumblr, Bluesky, DeviantArt and other sources without editing the .env file.",
    "Configurar fontes": "Configure sources",
    "Os valores ficam somente neste dispositivo. Por segurança, credenciais salvas nunca são exibidas de volta; deixe um campo vazio para manter o valor atual.": "Values remain on this device only. For safety, saved credentials are never displayed again; leave a field empty to keep its current value.",
    "Salvar credenciais": "Save credentials",
    "Configurado — deixe vazio para manter": "Configured — leave empty to keep",
    "Digite o valor": "Enter value",
    "Remover": "Remove",
    "configuradas": "configured",
    "Credenciais salvas neste dispositivo.": "Credentials saved on this device.",
    "Erro ao salvar credenciais": "Could not save credentials",
    "Parear PC e celular": "Pair PC and phone",
    "Transfira tags e credenciais em um pacote criptografado, temporário e sem nuvem.": "Transfer tags and credentials in a temporary encrypted package without cloud storage.",
    "Parear dispositivo": "Pair device",
    "Conecte PC e celular ao mesmo Wi-Fi. O código expira em cinco minutos e funciona uma vez.": "Connect the PC and phone to the same Wi-Fi. The code expires in five minutes and works once.",
    "Transferir categorias e tags": "Transfer categories and tags",
    "Transferir credenciais configuradas": "Transfer configured credentials",
    "O QR contém a chave de descriptografia. Mostre-o somente ao seu próprio celular e não envie o código por mensagens.": "The QR contains the decryption key. Show it only to your own phone and do not send the code through messages.",
    "Criar código de pareamento": "Create pairing code",
    "Copiar código": "Copy code",
    "No PC, abra Stats → Parear dispositivo. Escaneie o QR com a câmera, copie o texto reconhecido e cole abaixo.": "On the PC, open Stats → Pair device. Scan the QR with the camera, copy the recognized text, and paste it below.",
    "Categorias": "Categories",
    "Mesclar com as deste celular": "Merge with categories on this phone",
    "Substituir as deste celular": "Replace categories on this phone",
    "A importação não transfere imagens, banco ou histórico. Credenciais já existentes só são alteradas quando o PC envia um novo valor.": "The import does not transfer images, the database, or history. Existing credentials change only when the PC sends a new value.",
    "Importar do PC": "Import from PC",
    "Verificando este dispositivo...": "Checking this device...",
    "Cole o código criado no PC.": "Paste the code created on the PC.",
    "Pronto para criar um código temporário.": "Ready to create a temporary code.",
    "Selecione algo para transferir.": "Select something to transfer.",
    "Criando pacote criptografado...": "Creating encrypted package...",
    "categorias": "categories",
    "credenciais": "credentials",
    "expira em": "expires in",
    "Código expirado. Crie outro para tentar novamente.": "Code expired. Create another one to try again.",
    "Código copiado.": "Code copied.",
    "Código de pareamento inválido.": "Invalid pairing code.",
    "O código não aponta para um PC na rede local.": "The code does not point to a PC on the local network.",
    "Este WebView não oferece criptografia segura.": "This WebView does not provide secure cryptography.",
    "Código expirado ou já utilizado.": "Code expired or already used.",
    "Não foi possível acessar o PC. Verifique o Wi-Fi e o firewall.": "Could not reach the PC. Check Wi-Fi and the firewall.",
    "Pacote incompatível.": "Incompatible package.",
    "Não foi possível validar ou descriptografar o pacote.": "Could not validate or decrypt the package.",
    "Importar tags e credenciais deste PC?": "Import tags and credentials from this PC?",
    "Recebendo e descriptografando...": "Receiving and decrypting...",
    "Pareamento concluído com": "Pairing completed with",
    "Configuração importada com segurança.": "Configuration imported securely.",
    "Anterior (←)": "Previous (←)",
    "Próxima (→)": "Next (→)",
    "Triagem:": "Review:",
    "tecla 1": "key 1",
    "tecla 2": "key 2",
    "tecla 3": "key 3",
    "tecla 4": "key 4",
    "Selecionar (espaço)": "Select (space)",
    "☐ Selecionar": "☐ Select",
    "↗ Ver original": "↗ View original",
    "Baixando imagens": "Downloading images",
    "Aguarde...": "Please wait...",
    "Preparando...": "Preparing...",
    "Fechar": "Close",
    "Confirmação": "Confirmation",
    "Confirmar": "Confirm",
    "Gerenciar Categorias": "Manage Categories",
    "Categorias salvas": "Saved categories",
    "Adicionar / Editar": "Add / Edit",
    "Nome": "Name",
    "ex: Vex, V (Cyberpunk)...": "e.g. Vex, V (Cyberpunk)...",
    "Cor": "Color",
    "Chave única": "Unique key",
    "gerada automaticamente a partir do nome": "automatically generated from the name",
    "Grupo / Fandom": "Group / Fandom",
    "ex: League of Legends, Cyberpunk 2077...": "e.g. League of Legends, Cyberpunk 2077...",
    "Tags de busca": "Search tags",
    "Cada linha (ou": "Each line (or",
    ") = busca independente — resultados são unidos (OR). Espaço entre tags = AND. Prefixo": ") = independent search — results are merged (OR). A space between tags = AND. Prefix",
    "exclui.": "excludes.",
    "Digite 2+ letras pra sugerir tags.": "Type 2+ letters to suggest tags.",
    "Favoritar no sidebar": "Favorite in sidebar",
    "Emoji (opcional)": "Emoji (optional)",
    "Salvar": "Save",
    "Limpar formulário": "Clear form",
    "✓ Selecionar / Desmarcar": "✓ Select / Deselect",
    "📌 Guardar (só URL)": "📌 Save (URL only)",
    "⬇️ Baixar": "⬇️ Download",
    "⬇ Salvar no celular": "⬇ Save to phone",
    "⭐ Favoritar Artista": "⭐ Favorite Artist",
    "🎨 Buscar este artista": "🎨 Search this artist",
    "↗️ Ver original": "↗️ View original",
    "🔍 Ampliar": "🔍 Enlarge",
    "🚫 Bloquear Artista": "🚫 Block Artist",
    "🚫 Ocultar para sempre": "🚫 Hide forever",
    "Erro": "Error",
    "Sem dados": "No data",
    "Configuração necessária": "Configuration required",
    "configurar": "configure",
    "Avaliação removida": "Review removed",
    "Erro ao salvar avaliação": "Could not save review",
    "Erro no download.": "Download failed.",
    "Erro ao carregar stats.": "Could not load statistics.",
    "Esta opção está disponível no aplicativo desktop.": "This option is available in the desktop application.",
    "Não foi possível abrir a pasta": "Could not open the folder"
    ,"Concluído ✓": "Completed ✓"
    ,"Remover avaliação": "Remove review"
    ,"Já baixado": "Already downloaded"
    ,"← Voltar à galeria": "← Back to gallery"
    ,"🗑 Apagar": "🗑 Delete"
    ,"Voltar": "Back"
    ,"Nenhuma duplicata encontrada entre as imagens baixadas. 🎉": "No duplicates found among downloaded images. 🎉"
    ,"Nenhum artista favoritado. Clique com o botão direito numa arte →": "No favorite artists yet. Right-click an artwork →"
    ,"Favoritar artista": "Favorite artist"
    ,"Nenhum resultado para este filtro.": "No results for this filter."
    ,"Nenhuma categoria": "No categories"
    ,"Selecione ao menos uma categoria.": "Select at least one category."
    ,"Selecione ao menos uma fonte.": "Select at least one source."
    ,"Selecione imagens primeiro.": "Select images first."
    ,"Selecione 2 a 4 imagens para comparar.": "Select 2 to 4 images to compare."
    ,"Nome e tags são obrigatórios.": "Name and tags are required."
    ,"Este post não tem artista identificado.": "This post has no identified artist."
    ,"As selecionadas são 'só-URL' — use Ocultar.": "The selected items are URL-only — use Hide."
    ,"Guardando arte...": "Saving artwork..."
    ,"📌 Arte guardada na Galeria!": "📌 Artwork saved to Gallery!"
    ,"📌 Guardado na Galeria!": "📌 Saved to Gallery!"
    ,"Erro na busca.": "Search failed."
    ,"Erro ao salvar ordem": "Could not save order"
    ,"Erro ao carregar categorias": "Could not load categories"
    ,"Erro ao carregar galeria": "Could not load gallery"
    ,"Erro ao guardar": "Could not save"
    ,"Erro visualizando galeria": "Could not display gallery"
    ,"Erro ao bloquear": "Could not block"
    ,"Erro JSON no EventSource": "EventSource JSON error"
    ,"Apagar Arquivo": "Delete File"
    ,"Apagar do dispositivo": "Delete from device"
    ,"Salvar na Galeria do celular": "Save to phone Gallery"
    ,"Salva na Galeria do celular": "Saved to phone Gallery"
    ,"Baixar no ArtFinder e salvar em Pictures/ArtFinder": "Download in ArtFinder and save to Pictures/ArtFinder"
    ,"Imagem salva em Pictures/ArtFinder.": "Image saved to Pictures/ArtFinder."
    ,"As imagens selecionadas já estão na Galeria do celular.": "The selected images are already in the phone Gallery."
    ,"Apagar do disco": "Delete from disk"
    ,"Ocultar Arte": "Hide Artwork"
    ,"Ocultar selecionadas": "Hide selected"
    ,"Bloquear Artista": "Block Artist"
    ,"Remover Guardado": "Remove Saved Item"
    ,"Apagar esta imagem do HD definitivamente?": "Permanently delete this image from disk?"
    ,"Apagar esta imagem do dispositivo definitivamente?": "Permanently delete this image from the device?"
    ,"Você quer excluir definitivamente este arquivo do seu HD e da galeria?": "Permanently delete this file from disk and from the gallery?"
    ,"Você quer excluir definitivamente este arquivo do dispositivo e da Galeria do celular?": "Permanently delete this file from the device and the phone Gallery?"
    ,"Ocultar esta arte permanentemente? Ela nunca mais aparecerá nas buscas.": "Hide this artwork permanently? It will never appear in searches again."
    ,"Você quer remover essa imagem dos guardados?": "Remove this image from saved items?"
    ,"⚠️ Apagar TODOS os registros do banco? (HD não afetado)": "⚠️ Delete ALL database records? (disk files are unaffected)"
    ,"Tem certeza?": "Are you sure?"
    ,"Remover do banco registros de arquivos apagados?": "Remove records for deleted files from the database?"
    ,"Próxima »": "Next »"
    ,"👁️ Mostrar todas": "👁️ Show all"
    ,"💔 Remover dos Guardados": "💔 Remove from Saved"
    ,"imagem indisponivel": "image unavailable"
  };

  const PATTERNS = [
    [/^≈ (\d+) posts por fonte$/, "≈ $1 posts per source"],
    [/^(\d+) imagem\(ns\) baixada\(s\)!$/, "$1 image(s) downloaded!"],
    [/^(\d+) imagem\(ns\) salva\(s\) em Pictures\/ArtFinder!$/, "$1 image(s) saved to Pictures/ArtFinder!"],
    [/^(\d+) imagem\(ns\) salva\(s\) em Pictures\/ArtFinder\.$/, "$1 image(s) saved to Pictures/ArtFinder."],
    [/^(\d+) salva\(s\) no ArtFinder; (\d+) aguardando exportação para a Galeria\.$/, "$1 saved in ArtFinder; $2 waiting to be exported to the Gallery."],
    [/^(\d+) arte\(s\) guardada\(s\) na Galeria!$/, "$1 artwork item(s) saved to the Gallery!"],
    [/^Guardando (\d+) arte\(s\)\.\.\.$/, "Saving $1 artwork item(s)..."],
    [/^Mostrando página (\d+) de (\d+) \((\d+) imagens no total\)$/, "Showing page $1 of $2 ($3 images total)"],
    [/^Configuração necessária: (.+)$/, "Configuration required: $1"],
    [/^Erro: (.+)$/, "Error: $1"],
    [/^(\d+) selecionada\(s\)$/, "$1 selected"],
    [/^(\d+) grupo\(s\) de quase-duplicatas\.(.*)$/, "$1 near-duplicate group(s).$2"]
    ,[/^Guardando arte\.\.\.$/, "Saving artwork..."]
    ,[/^(\d+) arte\(s\) ocultada\(s\)\.$/, "$1 artwork item(s) hidden."]
    ,[/^Ocultar (\d+) arte\(s\) permanentemente\? Não aparecerão mais nas buscas nem na galeria\.$/, "Hide $1 artwork item(s) permanently? They will no longer appear in searches or the gallery."]
    ,[/^Apagar (\d+) arquivo\(s\) do HD definitivamente\?(.*)$/, "Permanently delete $1 file(s) from disk?$2"]
    ,[/^Apagar (\d+) arquivo\(s\) do dispositivo definitivamente\?(.*)$/, "Permanently delete $1 file(s) from the device?$2"]
    ,[/^ \((\d+) guardada\(s\) só-URL serão ignoradas\)$/, " ($1 URL-only saved item(s) will be ignored)"]
    ,[/^Você quer realmente bloquear o artista "(.+)"\? Todas as artes desse artista sumirão da tela agora e não aparecerão em buscas futuras\.$/, "Do you really want to block artist \"$1\"? All of this artist's artwork will disappear now and will not appear in future searches."]
    ,[/^A maior resolução está marcada em verde \(recomendada pra manter\)\.$/, "The highest resolution is marked in green (recommended to keep)."]
    ,[/^❌ Erro: (.+)$/, "❌ Error: $1"]
    ,[/^Erro ao ([^:]+): (.+)$/, "Could not $1: $2"]
  ];

  let language = localStorage.getItem(STORAGE_KEY);
  if (!SUPPORTED.has(language)) {
    language = navigator.language?.toLowerCase().startsWith("en") ? "en" : "pt-BR";
  }

  function translateRaw(raw, target = language) {
    if (target === "pt-BR" || !raw) return raw;
    if (EN[raw]) return EN[raw];
    for (const [pattern, replacement] of PATTERNS) {
      if (pattern.test(raw)) return raw.replace(pattern, replacement);
    }
    return raw;
  }

  function translateTextNode(node) {
    if (!node.parentElement || node.parentElement.closest("script,style,[data-i18n-skip]")) return;
    const current = node.nodeValue || "";
    const trimmed = current.trim();
    if (!trimmed) return;
    if (node.__artfinderI18nSource === undefined) node.__artfinderI18nSource = trimmed;
    const translated = translateRaw(node.__artfinderI18nSource);
    node.nodeValue = current.replace(trimmed, translated);
  }

  function translateAttributes(element) {
    if (!(element instanceof Element) || element.closest("[data-i18n-skip]")) return;
    for (const attr of ["title", "placeholder", "aria-label"]) {
      if (!element.hasAttribute(attr)) continue;
      const property = `artfinderI18n${attr.replace("-", "_")}`;
      if (element.dataset[property] === undefined) element.dataset[property] = element.getAttribute(attr);
      element.setAttribute(attr, translateRaw(element.dataset[property]));
    }
  }

  function applyTranslations(root = document) {
    if (root.nodeType === Node.TEXT_NODE) {
      translateTextNode(root);
      return;
    }
    if (!(root instanceof Document || root instanceof Element)) return;
    if (root instanceof Element) translateAttributes(root);
    root.querySelectorAll("*").forEach(translateAttributes);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) translateTextNode(walker.currentNode);
    document.documentElement.lang = language;
    const select = document.getElementById("languageSelect");
    if (select) select.value = language;
  }

  function setLanguage(next) {
    if (!SUPPORTED.has(next)) return;
    language = next;
    localStorage.setItem(STORAGE_KEY, language);
    applyTranslations(document);
    window.dispatchEvent(new CustomEvent("artfinder:language", {detail: {language}}));
  }

  window.t = (source, values = {}) => {
    let result = translateRaw(source);
    for (const [key, value] of Object.entries(values)) result = result.replaceAll(`{${key}}`, value);
    return result;
  };
  window.setLanguage = setLanguage;
  window.getLanguage = () => language;
  window.applyTranslations = applyTranslations;

  document.addEventListener("DOMContentLoaded", () => {
    applyTranslations(document);
    const observer = new MutationObserver(records => {
      for (const record of records) record.addedNodes.forEach(applyTranslations);
    });
    observer.observe(document.body, {childList: true, subtree: true});
  });
})();
