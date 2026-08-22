package io.github.gabizips.artfinder

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import io.github.gabizips.artfinder.data.PairingImport
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.GalleryItem
import io.github.gabizips.artfinder.model.SettingsSnapshot
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class SearchUiState(
    val loading: Boolean = false,
    val posts: List<ArtPost> = emptyList(),
    val errors: Map<ArtSource, String> = emptyMap(),
    val selectedCategory: String? = null,
    val selectedSources: Set<ArtSource> = setOf(ArtSource.DANBOORU, ArtSource.SAFEBOORU, ArtSource.E621),
    val message: String? = null,
    val saving: Set<String> = emptySet(),
)

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val app = application
    private val container = (application as ArtFinderApplication).container
    val settings: StateFlow<SettingsSnapshot> = container.settings.snapshot.stateIn(
        viewModelScope, SharingStarted.WhileSubscribed(5_000), SettingsSnapshot(),
    )
    val searchState = MutableStateFlow(SearchUiState())
    val pairingBusy = MutableStateFlow(false)
    val pairingMessage = MutableStateFlow<String?>(null)
    val pairingError = MutableStateFlow(false)

    fun selectCategory(key: String) { searchState.value = searchState.value.copy(selectedCategory = key) }
    fun toggleSource(source: ArtSource) {
        val current = searchState.value.selectedSources
        val next = if (source in current) current - source else current + source
        searchState.value = searchState.value.copy(selectedSources = next)
    }

    fun search(pages: Int = 1) = viewModelScope.launch {
        val state = searchState.value
        val category = settings.value.categories.firstOrNull { it.key == state.selectedCategory }
            ?: settings.value.categories.firstOrNull()
        if (category == null || state.selectedSources.isEmpty()) {
            searchState.value = state.copy(message = app.getString(R.string.choose_tag_source))
            return@launch
        }
        searchState.value = state.copy(loading = true, message = null, selectedCategory = category.key)
        runCatching {
            container.search.search(category, state.selectedSources, pages, container.settings.credentials())
        }.onSuccess { outcome ->
            searchState.value = searchState.value.copy(loading = false, posts = outcome.posts, errors = outcome.errors)
        }.onFailure { error ->
            searchState.value = searchState.value.copy(loading = false, message = error.message ?: app.getString(R.string.search_failed))
        }
    }

    fun importPairing(code: String, replace: Boolean) = viewModelScope.launch {
        pairingBusy.value = true
        pairingMessage.value = null
        pairingError.value = false
        runCatching { container.pairing.receive(code.trim()) }
            .onSuccess { imported: PairingImport ->
                container.settings.importConfiguration(imported.categories, imported.credentials, replace)
                val tagCount = imported.categories?.size ?: 0
                val credentialCount = imported.credentials.size
                pairingMessage.value = app.getString(
                    R.string.import_success,
                    app.resources.getQuantityString(R.plurals.imported_tags, tagCount, tagCount),
                    app.resources.getQuantityString(R.plurals.imported_credentials, credentialCount, credentialCount),
                )
            }
            .onFailure {
                pairingError.value = true
                pairingMessage.value = it.message ?: app.getString(R.string.import_failed)
            }
        pairingBusy.value = false
    }

    fun upsertCategory(category: Category) = viewModelScope.launch {
        runCatching { container.settings.upsertCategory(category) }
            .onFailure { searchState.value = searchState.value.copy(message = it.message) }
    }

    fun deleteCategory(key: String) = viewModelScope.launch { container.settings.deleteCategory(key) }

    fun saveCredential(key: String, value: String) = viewModelScope.launch {
        runCatching { container.settings.saveCredential(key, value) }
            .onSuccess {
                pairingError.value = false
                pairingMessage.value = app.getString(R.string.credential_saved)
            }
            .onFailure {
                pairingError.value = true
                pairingMessage.value = it.message
            }
    }

    fun save(post: ArtPost) = viewModelScope.launch {
        val uid = "${post.source.id}:${post.id}"
        searchState.value = searchState.value.copy(saving = searchState.value.saving + uid, message = null)
        runCatching { container.gallery.save(post) }
            .onSuccess { searchState.value = searchState.value.copy(message = app.getString(R.string.saved_gallery)) }
            .onFailure { searchState.value = searchState.value.copy(message = it.message ?: app.getString(R.string.save_failed)) }
        searchState.value = searchState.value.copy(saving = searchState.value.saving - uid)
    }

    fun delete(item: GalleryItem) = viewModelScope.launch { container.gallery.delete(item) }

    fun clearMessages() {
        searchState.value = searchState.value.copy(message = null)
        pairingMessage.value = null
        pairingError.value = false
    }
}
