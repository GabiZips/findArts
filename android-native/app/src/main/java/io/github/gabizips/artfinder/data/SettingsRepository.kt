package io.github.gabizips.artfinder.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.GalleryItem
import io.github.gabizips.artfinder.model.SettingsSnapshot
import io.github.gabizips.artfinder.model.SearchOptions
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.artFinderDataStore by preferencesDataStore(name = "artfinder")

class SettingsRepository(private val context: Context) {
    private val categoriesKey = stringPreferencesKey("categories_v1")
    private val credentialsKey = stringPreferencesKey("encrypted_credentials_v1")
    private val galleryKey = stringPreferencesKey("gallery_v1")
    private val legacyMigrationKey = booleanPreferencesKey("legacy_python_migrated_v1")
    private val searchPagesKey = intPreferencesKey("search_pages_v1")
    private val searchSfwKey = booleanPreferencesKey("search_sfw_v1")
    private val searchSensitiveKey = booleanPreferencesKey("search_sensitive_v1")
    private val searchNsfwKey = booleanPreferencesKey("search_nsfw_v1")
    private val searchPeriodKey = intPreferencesKey("search_period_days_v1")
    private val searchMinScoreKey = intPreferencesKey("search_min_score_v1")
    private val searchHideAiKey = booleanPreferencesKey("search_hide_ai_v1")
    private val vault = CredentialVault()

    val snapshot: Flow<SettingsSnapshot> = context.artFinderDataStore.data.map { preferences ->
        val encrypted = JsonCodec.stringMapFromJson(preferences[credentialsKey].orEmpty())
        SettingsSnapshot(
            categories = runCatching { JsonCodec.categoriesFromJson(preferences[categoriesKey].orEmpty()) }.getOrDefault(emptyList()),
            gallery = runCatching { JsonCodec.galleryFromJson(preferences[galleryKey].orEmpty()) }.getOrDefault(emptyList()),
            configuredCredentials = encrypted.filterValues { vault.decrypt(it)?.isNotBlank() == true }.keys,
            searchOptions = SearchOptions(
                pages = (preferences[searchPagesKey] ?: 5).coerceIn(1, 25),
                includeSfw = preferences[searchSfwKey] ?: true,
                includeSensitive = preferences[searchSensitiveKey] ?: true,
                includeNsfw = preferences[searchNsfwKey] ?: false,
                periodDays = preferences[searchPeriodKey] ?: 0,
                minScore = (preferences[searchMinScoreKey] ?: 0).coerceAtLeast(0),
                hideAi = preferences[searchHideAiKey] ?: true,
            ),
        )
    }

    suspend fun saveSearchOptions(options: SearchOptions) {
        require(options.includeSfw || options.includeSensitive || options.includeNsfw)
        context.artFinderDataStore.edit { preferences ->
            preferences[searchPagesKey] = options.pages.coerceIn(1, 25)
            preferences[searchSfwKey] = options.includeSfw
            preferences[searchSensitiveKey] = options.includeSensitive
            preferences[searchNsfwKey] = options.includeNsfw
            preferences[searchPeriodKey] = options.periodDays.coerceAtLeast(0)
            preferences[searchMinScoreKey] = options.minScore.coerceAtLeast(0)
            preferences[searchHideAiKey] = options.hideAi
        }
    }

    suspend fun credentials(): Map<String, String> {
        val raw = context.artFinderDataStore.data.first()[credentialsKey].orEmpty()
        return JsonCodec.stringMapFromJson(raw).mapNotNull { (key, value) ->
            vault.decrypt(value)?.takeIf(String::isNotBlank)?.let { key to it }
        }.toMap()
    }

    suspend fun saveCredential(key: String, value: String) {
        require(key in ALLOWED_CREDENTIALS)
        require(value.length <= 4096 && value.none { it == '\n' || it == '\r' || it == '\u0000' })
        context.artFinderDataStore.edit { preferences ->
            val existing = JsonCodec.stringMapFromJson(preferences[credentialsKey].orEmpty()).toMutableMap()
            if (value.isBlank()) existing.remove(key) else existing[key] = vault.encrypt(value.trim())
            preferences[credentialsKey] = JsonCodec.stringMapToJson(existing)
        }
    }

    suspend fun importConfiguration(categories: List<Category>?, credentials: Map<String, String>, replace: Boolean) {
        context.artFinderDataStore.edit { preferences ->
            categories?.let { imported ->
                val final = if (replace) imported else {
                    val existing = JsonCodec.categoriesFromJson(preferences[categoriesKey].orEmpty())
                    (existing.associateBy(Category::key) + imported.associateBy(Category::key)).values.toList()
                }
                preferences[categoriesKey] = JsonCodec.categoriesToJson(final)
            }
            if (credentials.isNotEmpty()) {
                val encrypted = JsonCodec.stringMapFromJson(preferences[credentialsKey].orEmpty()).toMutableMap()
                credentials.forEach { (key, value) ->
                    if (key in ALLOWED_CREDENTIALS && value.isNotBlank()) encrypted[key] = vault.encrypt(value.trim())
                }
                preferences[credentialsKey] = JsonCodec.stringMapToJson(encrypted)
            }
        }
    }

    suspend fun upsertCategory(category: Category) {
        require(category.key.matches(Regex("[a-z0-9_-]{1,200}")))
        require(category.tags.isNotBlank() && category.tags.length <= 20_000)
        context.artFinderDataStore.edit { preferences ->
            val existing = JsonCodec.categoriesFromJson(preferences[categoriesKey].orEmpty()).toMutableList()
            existing.removeAll { it.key == category.key }
            existing.add(category)
            preferences[categoriesKey] = JsonCodec.categoriesToJson(existing)
        }
    }

    suspend fun deleteCategory(key: String) {
        context.artFinderDataStore.edit { preferences ->
            val existing = JsonCodec.categoriesFromJson(preferences[categoriesKey].orEmpty()).filterNot { it.key == key }
            preferences[categoriesKey] = JsonCodec.categoriesToJson(existing)
        }
    }

    suspend fun addGalleryItem(item: GalleryItem) {
        context.artFinderDataStore.edit { preferences ->
            val items = JsonCodec.galleryFromJson(preferences[galleryKey].orEmpty()).filterNot { it.uid == item.uid }
            preferences[galleryKey] = JsonCodec.galleryToJson(listOf(item) + items)
        }
    }

    suspend fun removeGalleryItem(uid: String) {
        context.artFinderDataStore.edit { preferences ->
            val items = JsonCodec.galleryFromJson(preferences[galleryKey].orEmpty()).filterNot { it.uid == uid }
            preferences[galleryKey] = JsonCodec.galleryToJson(items)
        }
    }

    suspend fun migrateLegacyPythonData() {
        val preferences = context.artFinderDataStore.data.first()
        if (preferences[legacyMigrationKey] == true) return
        val candidates = listOf(
            context.filesDir.resolve("app/artfinder"),
            context.filesDir.resolve("artfinder"),
        )
        val legacy = candidates.firstOrNull { it.isDirectory }
        if (legacy != null) {
            val categories = runCatching {
                val root = org.json.JSONObject(legacy.resolve("user_categories.json").readText())
                JsonCodec.categoriesFromJson(root.optJSONObject("categories")?.toString().orEmpty())
            }.getOrDefault(emptyList())
            val credentials = runCatching {
                legacy.resolve(".env").readLines().mapNotNull { line ->
                    val clean = line.trim()
                    if (clean.isBlank() || clean.startsWith('#') || '=' !in clean) return@mapNotNull null
                    val key = clean.substringBefore('=').trim()
                    val value = clean.substringAfter('=').trim().trim('"', '\'')
                    if (key in ALLOWED_CREDENTIALS && value.isNotBlank()) key to value else null
                }.toMap()
            }.getOrDefault(emptyMap())
            if (categories.isNotEmpty() || credentials.isNotEmpty()) {
                importConfiguration(categories.takeIf { it.isNotEmpty() }, credentials, replace = false)
                runCatching { legacy.resolve(".env").delete() }
            }
        }
        context.artFinderDataStore.edit { it[legacyMigrationKey] = true }
    }

    companion object {
        val ALLOWED_CREDENTIALS = setOf(
            "DANBOORU_LOGIN", "DANBOORU_API_KEY", "GELBOORU_USER_ID", "GELBOORU_API_KEY",
            "PIXIV_REFRESH_TOKEN", "TUMBLR_API_KEY", "TUMBLR_CONSUMER_SECRET",
            "TUMBLR_OAUTH_TOKEN", "TUMBLR_OAUTH_TOKEN_SECRET", "DEVIANTART_CLIENT_ID",
            "DEVIANTART_CLIENT_SECRET", "BSKY_HANDLE", "BSKY_PASSWORD",
        )
    }
}
