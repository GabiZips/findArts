package io.github.gabizips.artfinder.data.source

import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

internal class BlueskySource : SourceClient {
    override val source = ArtSource.BLUESKY

    override suspend fun search(category: Category, pages: Int, credentials: Map<String, String>) = withContext(Dispatchers.IO) {
        val handle = credentials["BSKY_HANDLE"].orEmpty()
        val password = credentials["BSKY_PASSWORD"].orEmpty()
        require(handle.isNotBlank() && password.isNotBlank()) { "Configure BSKY_HANDLE e uma app password." }
        val session = JSONObject(Http.postJson(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            JSONObject().put("identifier", handle).put("password", password),
        ))
        val token = session.getString("accessJwt")
        category.queriesFor(source).flatMap { rawQuery ->
            val query = category.sourceTags[source.id]?.firstOrNull()?.takeIf(String::isNotBlank)
                ?: derivedTextQuery(rawQuery)
            var cursor: String? = null
            buildList {
                for (page in 0 until pages) {
                    val root = JSONObject(Http.get(
                        "https://bsky.social/xrpc/app.bsky.feed.searchPosts",
                        mapOf("q" to query, "limit" to 100, "cursor" to cursor),
                        mapOf("Authorization" to "Bearer $token"),
                    ))
                    val posts = root.optJSONArray("posts") ?: JSONArray()
                    for (index in 0 until posts.length()) {
                        val post = posts.optJSONObject(index) ?: continue
                        val embed = post.optJSONObject("embed") ?: continue
                        val images = embed.optJSONArray("images") ?: continue
                        val author = post.optJSONObject("author") ?: JSONObject()
                        val record = post.optJSONObject("record") ?: JSONObject()
                        val uri = post.string("uri")
                        val postId = uri.substringAfterLast('/')
                        val tags = extractBlueskyTags(record)
                        val labels = post.optJSONArray("labels") ?: JSONArray()
                        val nsfw = (0 until labels.length()).any { labels.optJSONObject(it)?.string("val") in NSFW_TERMS }
                        for (imageIndex in 0 until images.length()) {
                            val image = images.optJSONObject(imageIndex) ?: continue
                            val aspect = image.optJSONObject("aspectRatio") ?: JSONObject()
                            val url = image.string("fullsize")
                            val width = aspect.int("width")
                            val height = aspect.int("height")
                            val rating = if (nsfw || tags.lowercase().split(' ').any { it in NSFW_TERMS }) "nsfw" else "sfw"
                            if (url.isBlank() || !isAccepted(width, height, rating, tags)) continue
                            val id = if (images.length() > 1) "${postId}_$imageIndex" else postId
                            add(ArtPost(
                                id = id, source = source, url = url,
                                previewUrl = image.string("thumb").ifBlank { url },
                                pageUrl = "https://bsky.app/profile/${author.string("handle")}/post/$postId",
                                width = width, height = height, score = post.int("likeCount"),
                                artist = author.string("displayName").ifBlank { author.string("handle") },
                                tags = tags, rating = rating, categoryKey = category.key,
                            ))
                        }
                    }
                    cursor = root.string("cursor").takeIf(String::isNotBlank)
                    if (cursor == null || posts.length() == 0) break
                }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }
    }

    private fun extractBlueskyTags(record: JSONObject): String {
        val tags = linkedSetOf<String>()
        val facets = record.optJSONArray("facets") ?: JSONArray()
        for (index in 0 until facets.length()) {
            val features = facets.optJSONObject(index)?.optJSONArray("features") ?: continue
            for (featureIndex in 0 until features.length()) {
                features.optJSONObject(featureIndex)?.string("tag")?.takeIf(String::isNotBlank)?.let(tags::add)
            }
        }
        Regex("#([\\p{L}\\p{N}_-]+)").findAll(record.string("text")).forEach { tags += it.groupValues[1] }
        return tags.joinToString(" ")
    }

    private companion object {
        val NSFW_TERMS = setOf("porn", "sexual", "nudity", "nsfw", "explicit", "graphic-media", "r18", "18+")
    }
}

internal class TumblrSource : SourceClient {
    override val source = ArtSource.TUMBLR

    override suspend fun search(category: Category, pages: Int, credentials: Map<String, String>) = withContext(Dispatchers.IO) {
        val apiKey = credentials["TUMBLR_API_KEY"].orEmpty()
        require(apiKey.isNotBlank()) { "Configure TUMBLR_API_KEY." }
        val offsets = listOf(0, 30, 90, 180, 365).take(pages)
        val now = System.currentTimeMillis() / 1000
        category.queriesFor(source).flatMap { rawQuery ->
            val tags = if (category.sourceTags[source.id].isNullOrEmpty()) {
                derivedTextQuery(rawQuery).split(Regex("\\s{2,}")).filter(String::isNotBlank)
            } else listOf(rawQuery)
            tags.flatMap { tag ->
                offsets.flatMap { days ->
                    val params = mutableMapOf<String, Any?>("tag" to tag, "api_key" to apiKey, "limit" to 20, "npf" to "true")
                    if (days > 0) params["before"] = now - days * 86_400L
                    val root = JSONObject(Http.get("https://api.tumblr.com/v2/tagged", params))
                    val posts = root.optJSONArray("response") ?: JSONArray()
                    (0 until posts.length()).flatMap { index ->
                        val post = posts.optJSONObject(index) ?: return@flatMap emptyList()
                        val postTags = post.optJSONArray("tags")?.let { array ->
                            (0 until array.length()).joinToString(" ") { array.optString(it) }
                        }.orEmpty()
                        if (containsAi(postTags)) return@flatMap emptyList()
                        val postId = post.string("id")
                        extractTumblrImages(post).mapIndexedNotNull { imageIndex, image ->
                            if (!isAccepted(image.width, image.height, "sfw", postTags)) return@mapIndexedNotNull null
                            ArtPost(
                                id = if (imageIndex == 0) postId else "${postId}_$imageIndex",
                                source = source, url = image.url, previewUrl = image.preview,
                                pageUrl = post.string("post_url"), width = image.width, height = image.height,
                                score = post.int("note_count"), artist = post.string("blog_name"),
                                tags = postTags, categoryKey = category.key, postDate = post.long("timestamp"),
                            )
                        }
                    }
                }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }.sortedByDescending(ArtPost::score)
    }

    private data class TumblrImage(val url: String, val preview: String, val width: Int, val height: Int)

    private fun extractTumblrImages(post: JSONObject): List<TumblrImage> {
        val output = mutableListOf<TumblrImage>()
        fun blocks(array: JSONArray?) {
            if (array == null) return
            for (index in 0 until array.length()) {
                val block = array.optJSONObject(index) ?: continue
                if (block.string("type") != "image") continue
                media(block.optJSONArray("media"))?.let(output::add)
            }
        }
        blocks(post.optJSONArray("content"))
        val trail = post.optJSONArray("trail") ?: JSONArray()
        for (index in 0 until trail.length()) blocks(trail.optJSONObject(index)?.optJSONArray("content"))
        if (output.isEmpty()) {
            val photos = post.optJSONArray("photos") ?: JSONArray()
            for (index in 0 until photos.length()) media(photos.optJSONObject(index)?.optJSONArray("alt_sizes"))?.let(output::add)
        }
        return output.distinctBy(TumblrImage::url)
    }

    private fun media(array: JSONArray?): TumblrImage? {
        if (array == null || array.length() == 0) return null
        val options = (0 until array.length()).mapNotNull(array::optJSONObject)
        val best = options.maxByOrNull { it.int("width") * it.int("height") } ?: return null
        val url = best.string("url")
        if (url.isBlank()) return null
        val preview = options.filter { it.int("width") >= 400 }.minByOrNull { it.int("width") }?.string("url").orEmpty().ifBlank { url }
        return TumblrImage(url, preview, best.int("width"), best.int("height"))
    }
}

internal class DeviantArtSource : SourceClient {
    override val source = ArtSource.DEVIANTART

    override suspend fun search(category: Category, pages: Int, credentials: Map<String, String>) = withContext(Dispatchers.IO) {
        val clientId = credentials["DEVIANTART_CLIENT_ID"].orEmpty()
        val clientSecret = credentials["DEVIANTART_CLIENT_SECRET"].orEmpty()
        require(clientId.isNotBlank() && clientSecret.isNotBlank()) { "Configure as credenciais do DeviantArt." }
        val token = JSONObject(Http.postForm("https://www.deviantart.com/oauth2/token", mapOf(
            "grant_type" to "client_credentials", "client_id" to clientId, "client_secret" to clientSecret,
        ))).getString("access_token")
        category.queriesFor(source).flatMap { rawQuery ->
            val tag = if (category.sourceTags[source.id].isNullOrEmpty()) derivedTextQuery(rawQuery) else rawQuery
            (0 until pages).flatMap { page ->
                val root = JSONObject(Http.get(
                    "https://www.deviantart.com/api/v1/oauth2/browse/tags",
                    mapOf("tag" to tag, "offset" to page * 24, "limit" to 24, "mature_content" to "true"),
                    mapOf("Authorization" to "Bearer $token"),
                ))
                val results = root.optJSONArray("results") ?: JSONArray()
                (0 until results.length()).mapNotNull { index ->
                    val item = results.optJSONObject(index) ?: return@mapNotNull null
                    if (item.optBoolean("is_deleted") || item.optBoolean("is_mature")) return@mapNotNull null
                    val content = item.optJSONObject("content") ?: item.optJSONObject("preview") ?: JSONObject()
                    val fallback = item.optJSONArray("thumbs")?.let { thumbs ->
                        (0 until thumbs.length()).mapNotNull(thumbs::optJSONObject).maxByOrNull { it.int("width") }
                    }
                    val media = if (content.string("src").isNotBlank()) content else fallback ?: JSONObject()
                    val url = media.string("src")
                    val width = media.int("width")
                    val height = media.int("height")
                    val title = item.string("title")
                    if (url.isBlank() || !isAccepted(width, height, "sfw", "$tag $title")) return@mapNotNull null
                    val id = item.string("deviationid").ifBlank { item.string("deviation_id") }
                    ArtPost(
                        id = id, source = source, url = url, previewUrl = url,
                        pageUrl = item.string("url"), width = width, height = height,
                        score = item.optJSONObject("stats")?.int("favourites") ?: 0,
                        artist = item.optJSONObject("author")?.string("username").orEmpty(),
                        tags = tag, categoryKey = category.key, postDate = item.long("published_time"),
                    )
                }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }
    }
}
