package io.github.gabizips.artfinder.model

data class Category(
    val key: String,
    val label: String,
    val tags: String,
    val group: String = "Geral",
    val emoji: String = "🎨",
    val color: String = "#6366F1",
    val favorite: Boolean = false,
    val sourceTags: Map<String, List<String>> = emptyMap(),
)

enum class ArtSource(val id: String, val label: String, val credentialKeys: List<String> = emptyList()) {
    DANBOORU("danbooru", "Danbooru", listOf("DANBOORU_LOGIN", "DANBOORU_API_KEY")),
    GELBOORU("gelbooru", "Gelbooru", listOf("GELBOORU_USER_ID", "GELBOORU_API_KEY")),
    SAFEBOORU("safebooru", "Safebooru"),
    E621("e621", "e621"),
    PIXIV("pixiv", "Pixiv", listOf("PIXIV_REFRESH_TOKEN")),
    TUMBLR("tumblr", "Tumblr", listOf("TUMBLR_API_KEY", "TUMBLR_CONSUMER_SECRET", "TUMBLR_OAUTH_TOKEN", "TUMBLR_OAUTH_TOKEN_SECRET")),
    BLUESKY("bluesky", "Bluesky", listOf("BSKY_HANDLE", "BSKY_PASSWORD")),
    DEVIANTART("deviantart", "DeviantArt", listOf("DEVIANTART_CLIENT_ID", "DEVIANTART_CLIENT_SECRET"));

    companion object {
        fun fromId(id: String): ArtSource? = entries.firstOrNull {
            it.id == id.lowercase() || (id.lowercase() == "bsky" && it == BLUESKY)
        }
    }
}

data class ArtPost(
    val id: String,
    val source: ArtSource,
    val url: String,
    val previewUrl: String = url,
    val pageUrl: String = "",
    val width: Int = 0,
    val height: Int = 0,
    val score: Int = 0,
    val artist: String = "",
    val tags: String = "",
    val rating: String = "sfw",
    val categoryKey: String,
    val postDate: Long = 0,
)

data class GalleryItem(
    val uid: String,
    val contentUri: String,
    val source: String,
    val sourceId: String,
    val pageUrl: String,
    val artist: String,
    val categoryKey: String,
    val savedAt: Long,
)

data class SearchOutcome(
    val posts: List<ArtPost>,
    val errors: Map<ArtSource, String>,
)

data class SettingsSnapshot(
    val categories: List<Category> = emptyList(),
    val gallery: List<GalleryItem> = emptyList(),
    val configuredCredentials: Set<String> = emptySet(),
)
