"""Small Qt text translator reusing the application's existing PT/EN catalog."""
import json
import re

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QApplication, QAbstractButton, QComboBox, QLabel, QLineEdit, QMenu, QTabWidget


NATIVE_EN = {
    "Buscar artes": "Search artwork",
    "Digite tags ou escolha categorias e fontes em Busca avançada.": "Enter tags or choose categories and sources in Advanced search.",
    "Filtre as artes que já estão na tela.": "Filter the artwork already on screen.",
    "Aplicar filtros": "Apply filters",
    "Abrir interface legada": "Open legacy interface",
    "Abre no navegador enquanto o ArtFinder estiver aberto.": "Opens in your browser while ArtFinder is running.",
    "Não foi possível abrir a interface legada.": "Could not open the legacy interface.",
    "Digite tags, personagens ou artistas…": "Enter tags, characters or artists…",
    "Busca avançada": "Advanced search",
    "Tamanho": "Size",
    "Abrir arte": "Open artwork",
    "Limpar filtros": "Clear filters",
    "Buscando artes…": "Searching artwork…",
    "Os resultados aparecem conforme chegam.": "Results appear as they arrive.",
    "Nenhuma arte com esses filtros": "No artwork matches these filters",
    "Limpe os filtros para ver os resultados carregados.": "Clear the filters to see loaded results.",
    "Sem resultados": "No results",
    "Experimente outras tags ou fontes.": "Try different tags or sources.",
    "Sua galeria está vazia": "Your gallery is empty",
    "Use Guardar em uma arte de Explorar para trazê-la para cá.": "Save an artwork from Explore to bring it here.",
    "Detalhes": "Details", "Prévia": "Preview", "Idioma": "Language", "Geral": "General",
    "Selecione uma arte": "Select an artwork", "Formato": "Format", "Dimensões": "Dimensions", "Conteúdo": "Content",
    "NSFW\nAbrir para revelar": "NSFW\nOpen to reveal",
    "Aparência": "Appearance", "Tema do aplicativo": "App theme",
    "Noturno": "Night", "Grafite": "Graphite", "Floresta": "Forest", "Claro": "Light",
    "Escolha as cores da interface. A mudança é aplicada na hora e salva automaticamente.": "Choose the interface colors. Changes apply immediately and are saved automatically.",
    "Explorar": "Explore", "Minha galeria": "My gallery", "Estatísticas": "Statistics",
    "Ocultar prévias NSFW": "Hide NSFW previews", "Biblioteca local": "Local library",
    "Filtrar por artista, categoria ou tag…": "Filter by artist, category or tag…",
    "Maior score": "Highest score", "Mais recentes": "Most recent", "Todas as coleções": "All collections",
    "Ocultar artes já guardadas": "Hide saved artwork", "Criar uma busca": "Create a search",
    "Escolha personagens, artistas e fontes para começar.": "Choose characters, artists and sources to get started.",
    "Nenhuma arte para mostrar": "No artwork to display",
    "Ajuste os filtros ou faça uma nova busca. Artes guardadas aparecem na galeria.": "Adjust the filters or start a new search. Saved artwork appears in your gallery.",
    "Duplo clique para abrir • Ctrl + clique para selecionar": "Double-click to open • Ctrl + click to select",
    "Nova categoria": "New category", "Suas categorias": "Your categories", "Filtrar categorias…": "Filter categories…",
    "Tags principais": "Main tags", "Chave": "Key", "Grupo": "Group", "Favoritar categoria": "Favorite category",
    "Salvar categoria": "Save category", "Consultas separadas por ponto e vírgula": "Separate queries with semicolons",
    "Opcional: consultas específicas desta fonte": "Optional: source-specific queries",
    "Organize sua galeria": "Organize your gallery", "Nova": "New", "Renomear": "Rename", "Excluir": "Delete",
    "Escolha categorias e fontes ou informe tags para uma busca avulsa.": "Choose categories and sources or enter tags for a one-off search.",
    "Tags avulsas; separe consultas com ponto e vírgula": "One-off tags; separate queries with semicolons",
    "Configure outras fontes em Configurações → Fontes e credenciais.": "Configure more sources in Settings → Sources and credentials.",
    "Refinar resultados": "Refine results", "Os filtros são aplicados às artes carregadas, sem uma nova busca.": "Filters apply to loaded artwork without another search.",
    "Mídia": "Media", "Imagem": "Image", "Vídeo": "Video", "Qualquer período": "Any time",
    "Excluir tags": "Exclude tags", "Tags separadas por vírgula": "Comma-separated tags",
    "Artes sem data informada continuam visíveis no filtro de período.": "Artwork with no known date remains visible when filtering by time.",
    "Os valores salvos ficam no cofre do sistema e não são exibidos. Deixe em branco para manter.": "Saved values stay in the system vault and are never displayed. Leave blank to keep them.",
    "Configurado — em branco para manter": "Configured — leave blank to keep", "Não configurado": "Not configured",
    "Salvar credenciais": "Save credentials", "Carregando fontes…": "Loading sources…",
    "Celular": "Phone", "Arquivos": "Files", "Arquivos e manutenção": "Files and maintenance",
    "Abrir pasta de downloads": "Open downloads folder", "Abrir pasta de dados": "Open data folder",
    "A sincronização remove registros de arquivos que já foram apagados fora do aplicativo.": "Synchronization removes records of files already deleted outside the app.",
    "Categorias e tags": "Categories and tags", "Credenciais das fontes": "Source credentials",
    "Use a mesma rede Wi-Fi. O código é temporário e inclui somente os itens selecionados.": "Use the same Wi-Fi network. The temporary code only includes the selected items.",
    "Gerar código de pareamento": "Generate pairing code", "Copiar código": "Copy code",
    "‹ Anterior": "‹ Previous", "Próxima ›": "Next ›", "Reproduzir / pausar": "Play / pause", "Ajustar": "Fit",
    "Abrir": "Open", "Biblioteca atualizada.": "Library updated.", "Artes guardadas na galeria.": "Artwork saved to your gallery.",
    "Carregando…": "Loading…", "Cancelar": "Cancel", "Filtros": "Filters", "Coleções": "Collections",
    "Arquivo": "File", "Nome": "Name", "Score mínimo": "Minimum score", "Período": "Time range",
    "Prévia indisponível": "Preview unavailable", "Artista desconhecido": "Unknown artist",
    "Conteúdo NSFW oculto. Revele somente se desejar visualizar.": "NSFW content is hidden. Reveal it only if you want to view it.",
}


class NativeTranslations(QObject):
    def __init__(self, resource_dir, language="pt-BR", parent=None):
        super().__init__(parent)
        self.language = language
        self.catalog = dict(NATIVE_EN)
        path = resource_dir / "templates" / "i18n.js"
        if path.is_file():
            dictionary = path.read_text(encoding="utf-8").split("const EN = {", 1)[-1].split("\n  };", 1)[0]
            for source, target in re.findall(r'("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*")', dictionary):
                self.catalog.setdefault(json.loads(source), json.loads(target))

    def text(self, text):
        return self.catalog.get(text, text) if self.language == "en" else text

    def attribute(self, widget, getter, setter, key):
        current = getter()
        previous = getattr(widget, "_af_" + key, None)
        source = previous[0] if previous and current == previous[1] else current
        translated = self.text(source)
        setattr(widget, "_af_" + key, (source, translated))
        if current != translated:
            setter(translated)

    def apply(self, widget):
        if widget.property("userDataLabels"):
            return
        if isinstance(widget, (QLabel, QAbstractButton)):
            self.attribute(widget, widget.text, widget.setText, "text")
        if isinstance(widget, QLineEdit):
            self.attribute(widget, widget.placeholderText, widget.setPlaceholderText, "placeholder")
        if isinstance(widget, QComboBox) and not widget.property("userDataLabels"):
            for index in range(widget.count()):
                self.attribute(widget, lambda i=index: widget.itemText(i), lambda value, i=index: widget.setItemText(i, value), f"item{index}")
        if isinstance(widget, QTabWidget):
            for index in range(widget.count()):
                self.attribute(widget, lambda i=index: widget.tabText(i), lambda value, i=index: widget.setTabText(i, value), f"tab{index}")
        if isinstance(widget, QMenu):
            for action in widget.actions():
                self.attribute(action, action.text, action.setText, "text")
        if widget.isWindow():
            self.attribute(widget, widget.windowTitle, widget.setWindowTitle, "title")

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and hasattr(watched, "isWindow"):
            self.apply(watched)
        return False

    def set_language(self, language):
        self.language = language
        for window in QApplication.topLevelWidgets():
            self.apply(window)
            for child in window.findChildren(QLabel) + window.findChildren(QAbstractButton) + window.findChildren(QLineEdit) + window.findChildren(QComboBox) + window.findChildren(QTabWidget):
                self.apply(child)
