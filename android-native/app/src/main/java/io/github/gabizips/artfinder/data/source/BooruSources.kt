package io.github.gabizips.artfinder.data.source

import android.util.Base64
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOptions
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

internal class DanbooruSource : SourceClient {
    override val source = ArtSource.DANBOORU

    override suspend fun search(category: Category, options: SearchOptions, credentials: Map<String, String>, tracker: RequestTracker) = withContext(Dispatchers.IO) {
        val login = credentials["DANBOORU_LOGIN"].orEmpty()
        val apiKey = credentials["DANBOORU_API_KEY"].orEmpty()
        val headers = if (login.isNotBlank() && apiKey.isNotBlank()) mapOf(
            "Authorization" to "Basic " + Base64.encodeToString("$login:$apiKey".toByteArray(), Base64.NO_WRAP),
        ) else emptyMap()
        category.queriesFor(source).flatMap { query ->
            buildList {
            for (page in 1..options.pages) {
                val raw = Http.get(
                    "https://danbooru.donmai.us/posts.json",
                    mapOf("tags" to query, "limit" to if (headers.isEmpty()) 20 else 200, "page" to page),
                    headers, tracker,
                )
                val posts = parseArrayOrObject(raw, "posts")
                if (posts.length() == 0) break
                addAll((0 until posts.length()).mapNotNull { index ->
                    val post = posts.optJSONObject(index) ?: return@mapNotNull null
                    val width = post.int("image_width")
                    val height = post.int("image_height")
                    val rating = when (post.string("rating")) { "e" -> "nsfw"; "q", "s" -> "sensitive"; else -> "sfw" }
                    val tags = post.string("tag_string")
                    val id = post.string("id")
                    val url = post.string("file_url").ifBlank { post.string("large_file_url") }
                    if (id.isBlank() || url.isBlank()) return@mapNotNull null
                    ArtPost(
                        id = id, source = source, url = url,
                        previewUrl = post.string("large_file_url").ifBlank { url },
                        pageUrl = "https://danbooru.donmai.us/posts/$id",
                        width = width, height = height, score = post.int("score"),
                        artist = post.string("tag_string_artist"), tags = tags, rating = rating,
                        categoryKey = category.key,
                        postDate = post.epochSeconds("created_at"),
                    )
                })
            }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }
    }
}

internal class GelbooruSource : SourceClient {
    override val source = ArtSource.GELBOORU

    override suspend fun search(category: Category, options: SearchOptions, credentials: Map<String, String>, tracker: RequestTracker) = withContext(Dispatchers.IO) {
        val key = credentials["GELBOORU_API_KEY"].orEmpty()
        val user = credentials["GELBOORU_USER_ID"].orEmpty()
        require(key.isNotBlank() && user.isNotBlank()) { "Configure GELBOORU_USER_ID e GELBOORU_API_KEY." }
        category.queriesFor(source).flatMap { query ->
            buildList {
            for (page in 0 until options.pages) {
                val raw = Http.get("https://gelbooru.com/index.php", mapOf(
                    "page" to "dapi", "s" to "post", "q" to "index", "json" to 1,
                    "tags" to query, "limit" to 100, "pid" to page, "api_key" to key, "user_id" to user,
                ), tracker = tracker)
                val posts = parseArrayOrObject(raw, "post")
                if (posts.length() == 0) break
                addAll(booruArray(posts, category, source) { id ->
                    "https://gelbooru.com/index.php?page=post&s=view&id=$id"
                })
            }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }
    }
}

internal class SafebooruSource : SourceClient {
    override val source = ArtSource.SAFEBOORU

    override suspend fun search(category: Category, options: SearchOptions, credentials: Map<String, String>, tracker: RequestTracker) = withContext(Dispatchers.IO) {
        category.queriesFor(source).flatMap { query ->
            buildList {
            for (page in 0 until options.pages) {
                val raw = Http.get("https://safebooru.org/index.php", mapOf(
                    "page" to "dapi", "s" to "post", "q" to "index", "json" to 1,
                    "tags" to query, "limit" to 100, "pid" to page,
                ), mapOf("Accept" to "application/json"), tracker)
                val posts = parseArrayOrObject(raw, "post")
                if (posts.length() == 0) break
                addAll(booruArray(posts, category, source) { id ->
                    "https://safebooru.org/index.php?page=post&s=view&id=$id"
                })
            }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }
    }
}

private fun booruArray(
    posts: org.json.JSONArray,
    category: Category,
    source: ArtSource,
    pageUrl: (String) -> String,
): List<ArtPost> = (0 until posts.length()).mapNotNull { index ->
    val post = posts.optJSONObject(index) ?: return@mapNotNull null
    val id = post.string("id")
    val width = post.int("width")
    val height = post.int("height")
    val tags = post.string("tags")
    val rawRating = post.string("rating").lowercase()
    val rating = when (rawRating) {
        "e", "explicit" -> "nsfw"
        "q", "questionable", "s", "sensitive" -> "sensitive"
        else -> "sfw"
    }
    val fallbackUrl = if (source == ArtSource.SAFEBOORU) {
        val directory = post.string("directory")
        val image = post.string("image")
        if (directory.isNotBlank() && image.isNotBlank()) "https://safebooru.org/images/$directory/$image" else ""
    } else ""
    val url = post.string("file_url").ifBlank { fallbackUrl }
    if (id.isBlank() || url.isBlank()) return@mapNotNull null
    ArtPost(
        id = id, source = source, url = url,
        previewUrl = post.string("sample_url").ifBlank { post.string("preview_url") }.ifBlank { url },
        pageUrl = pageUrl(id), width = width, height = height, score = post.int("score"),
        tags = tags, rating = rating, categoryKey = category.key,
        postDate = post.epochSeconds("created_at").takeIf { it > 0 } ?: post.epochSeconds("created"),
    )
}

internal class E621Source : SourceClient {
    override val source = ArtSource.E621

    override suspend fun search(category: Category, options: SearchOptions, credentials: Map<String, String>, tracker: RequestTracker) = withContext(Dispatchers.IO) {
        category.queriesFor(source).flatMap { query ->
            buildList {
            for (page in 1..options.pages) {
                val root = JSONObject(Http.get("https://e621.net/posts.json", mapOf("tags" to query, "limit" to 100, "page" to page), tracker = tracker))
                val posts = root.optJSONArray("posts") ?: org.json.JSONArray()
                if (posts.length() == 0) break
                addAll((0 until posts.length()).mapNotNull { index ->
                    val post = posts.optJSONObject(index) ?: return@mapNotNull null
                    val file = post.optJSONObject("file") ?: return@mapNotNull null
                    val sample = post.optJSONObject("sample")
                    val id = post.string("id")
                    val url = file.string("url")
                    val width = file.int("width")
                    val height = file.int("height")
                    val tagsObject = post.optJSONObject("tags") ?: JSONObject()
                    val tags = tagsObject.keys().asSequence().flatMap { key ->
                        val values = tagsObject.optJSONArray(key) ?: org.json.JSONArray()
                        (0 until values.length()).asSequence().map { values.optString(it) }
                    }.joinToString(" ")
                    val rating = when (post.string("rating")) { "e" -> "nsfw"; "q" -> "sensitive"; else -> "sfw" }
                    if (id.isBlank() || url.isBlank()) return@mapNotNull null
                    ArtPost(
                        id = id, source = source, url = url,
                        previewUrl = sample?.string("url").orEmpty().ifBlank { url },
                        pageUrl = "https://e621.net/posts/$id", width = width, height = height,
                        score = post.optJSONObject("score")?.int("total") ?: 0,
                        artist = tagsObject.optJSONArray("artist")?.optString(0).orEmpty(),
                        tags = tags, rating = rating, categoryKey = category.key,
                        postDate = post.epochSeconds("created_at"),
                    )
                })
            }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }
    }
}
