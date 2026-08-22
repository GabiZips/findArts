package io.github.gabizips.artfinder.data.source

import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOptions
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

internal class PixivSource : SourceClient {
    override val source = ArtSource.PIXIV

    override suspend fun search(category: Category, options: SearchOptions, credentials: Map<String, String>, tracker: RequestTracker) = withContext(Dispatchers.IO) {
        val refreshToken = credentials["PIXIV_REFRESH_TOKEN"].orEmpty()
        require(refreshToken.isNotBlank()) { "Configure PIXIV_REFRESH_TOKEN." }
        val authHeaders = pixivHeaders()
        val authRoot = JSONObject(Http.postForm(
            "https://oauth.secure.pixiv.net/auth/token",
            mapOf(
                "get_secure_url" to "1", "client_id" to CLIENT_ID, "client_secret" to CLIENT_SECRET,
                "grant_type" to "refresh_token", "refresh_token" to refreshToken,
            ),
            authHeaders, tracker,
        ))
        val auth = authRoot.optJSONObject("response") ?: authRoot
        val accessToken = auth.getString("access_token")
        val exact = !category.sourceTags[source.id].isNullOrEmpty()
        category.queriesFor(source).flatMap { rawQuery ->
            val query = if (exact) rawQuery else derivedTextQuery(rawQuery)
            var offset: Int? = null
            buildList {
                for (page in 0 until options.pages) {
                    val root = JSONObject(Http.get(
                        "https://app-api.pixiv.net/v1/search/illust",
                        mapOf(
                            "word" to query,
                            "search_target" to if (exact) "exact_match_for_tags" else "partial_match_for_tags",
                            "sort" to "date_desc", "filter" to "for_ios", "search_ai_type" to 0,
                            "offset" to offset,
                        ),
                        pixivHeaders() + ("Authorization" to "Bearer $accessToken"), tracker,
                    ))
                    val illustrations = root.optJSONArray("illusts") ?: JSONArray()
                    for (index in 0 until illustrations.length()) {
                        val item = illustrations.optJSONObject(index) ?: continue
                        val isAi = item.int("illust_ai_type") == 2
                        val id = item.string("id")
                        val width = item.int("width")
                        val height = item.int("height")
                        val rating = if (item.int("x_restrict") == 0) "sfw" else "nsfw"
                        val image = bestImage(item)
                        val tags = item.optJSONArray("tags")?.let { array ->
                            (0 until array.length()).joinToString(" ") { array.optJSONObject(it)?.string("name").orEmpty() }
                        }.orEmpty()
                        if (id.isBlank() || image.first.isBlank()) continue
                        add(ArtPost(
                            id = id, source = source, url = image.first, previewUrl = image.second,
                            pageUrl = "https://www.pixiv.net/artworks/$id", width = width, height = height,
                            score = item.int("total_bookmarks"),
                            artist = item.optJSONObject("user")?.string("name").orEmpty(),
                            tags = tags, rating = rating, categoryKey = category.key,
                            postDate = item.epochSeconds("create_date"), isAi = isAi,
                        ))
                    }
                    val next = root.string("next_url")
                    if (next.isBlank()) break
                    offset = Regex("[?&]offset=(\\d+)").find(next)?.groupValues?.get(1)?.toIntOrNull()
                        ?: ((offset ?: 0) + 30)
                }
            }
        }.distinctBy { "${it.source.id}:${it.id}" }.sortedByDescending(ArtPost::score)
    }

    private fun bestImage(item: JSONObject): Pair<String, String> {
        item.optJSONObject("meta_single_page")?.string("original_image_url")?.takeIf(String::isNotBlank)?.let { original ->
            return original to item.optJSONObject("image_urls")?.string("large").orEmpty().ifBlank { original }
        }
        val pages = item.optJSONArray("meta_pages") ?: JSONArray()
        if (pages.length() > 0) {
            val urls = pages.optJSONObject(0)?.optJSONObject("image_urls") ?: JSONObject()
            val original = urls.string("original").ifBlank { urls.string("large") }
            return original to urls.string("large").ifBlank { original }
        }
        val urls = item.optJSONObject("image_urls") ?: JSONObject()
        val original = urls.string("large").ifBlank { urls.string("medium") }
        return original to urls.string("medium").ifBlank { original }
    }

    private fun pixivHeaders(): Map<String, String> {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'+00:00'", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }
        val time = formatter.format(Date())
        val hash = MessageDigest.getInstance("MD5").digest((time + HASH_SECRET).toByteArray())
            .joinToString("") { "%02x".format(it) }
        return mapOf(
            "App-OS" to "ios", "App-OS-Version" to "14.6",
            "User-Agent" to "PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)",
            "X-Client-Time" to time, "X-Client-Hash" to hash,
        )
    }

    private companion object {
        const val CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
        const val CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
        const val HASH_SECRET = "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"
    }
}
