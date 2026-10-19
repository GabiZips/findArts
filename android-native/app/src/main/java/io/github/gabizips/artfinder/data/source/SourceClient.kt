package io.github.gabizips.artfinder.data.source

import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.FormBody
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

internal const val USER_AGENT = "ArtFinder-Android/0.10.1 (+https://github.com/GabiZips/findArts)"

internal val AI_TAGS = setOf(
    "ai_generated", "ai-generated", "ai_art", "stable_diffusion", "novelai",
    "nai_diffusion", "midjourney", "dall-e", "dall_e", "image_generation",
    "automated_art", "diffusion_model", "generated_by_ai", "aigc", "aiart",
    "stablediffusion", "artificialintelligence", "aiillustration",
)

internal interface SourceClient {
    val source: ArtSource
    suspend fun search(
        category: Category,
        options: SearchOptions,
        credentials: Map<String, String>,
        tracker: RequestTracker,
    ): List<ArtPost>
}

internal class RequestTracker(private val onChanged: (Int) -> Unit = {}) {
    private val requests = AtomicInteger(0)
    val count: Int get() = requests.get()
    fun requestStarted() = onChanged(requests.incrementAndGet())
}

internal object Http {
    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()

    suspend fun get(
        url: String,
        params: Map<String, Any?> = emptyMap(),
        headers: Map<String, String> = emptyMap(),
        tracker: RequestTracker,
    ): String {
        val builder = url.toHttpUrl().newBuilder()
        params.forEach { (key, value) -> if (value != null) builder.addQueryParameter(key, value.toString()) }
        val request = Request.Builder().url(builder.build()).header("User-Agent", USER_AGENT).apply {
            headers.forEach { (key, value) -> header(key, value) }
        }.build()
        return execute(request, tracker)
    }

    suspend fun postForm(
        url: String,
        params: Map<String, String>,
        headers: Map<String, String> = emptyMap(),
        tracker: RequestTracker,
    ): String {
        val body = FormBody.Builder().apply { params.forEach { (key, value) -> add(key, value) } }.build()
        val request = Request.Builder().url(url).post(body).header("User-Agent", USER_AGENT).apply {
            headers.forEach { (key, value) -> header(key, value) }
        }.build()
        return execute(request, tracker)
    }

    suspend fun postJson(
        url: String,
        value: JSONObject,
        headers: Map<String, String> = emptyMap(),
        tracker: RequestTracker,
    ): String {
        val body = value.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder().url(url).post(body).header("User-Agent", USER_AGENT).apply {
            headers.forEach { (key, headerValue) -> header(key, headerValue) }
        }.build()
        return execute(request, tracker)
    }

    private suspend fun execute(request: Request, tracker: RequestTracker): String = suspendCancellableCoroutine { continuation ->
        tracker.requestStarted()
        val call = client.newCall(request)
        continuation.invokeOnCancellation { call.cancel() }
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                if (continuation.isActive) continuation.resumeWithException(e)
            }

            override fun onResponse(call: Call, response: Response) {
                val result = runCatching {
                    response.use {
                        val text = it.body.string()
                        if (!it.isSuccessful) throw IOException("HTTP ${it.code}: ${text.take(180)}")
                        text
                    }
                }
                if (!continuation.isActive) return
                result.fold(continuation::resume, continuation::resumeWithException)
            }
        })
    }
}

internal fun Category.queriesFor(source: ArtSource): List<String> {
    sourceTags[source.id]?.filter(String::isNotBlank)?.distinct()?.let { if (it.isNotEmpty()) return it }
    KnownMappings.find(source, this)?.let { return it.distinct() }
    return tags.split(';', '\n').map(String::trim).filter(String::isNotBlank).distinct().ifEmpty { listOf(key) }
}

private object KnownMappings {
    private val pixiv = mapOf(
        "shadow_solo" to listOf("シャドウ・ザ・ヘッジホッグ", "shadow_the_hedgehog"),
        "shadow_the_hedgehog" to listOf("シャドウ・ザ・ヘッジホッグ", "shadow_the_hedgehog"),
        "rouge_solo" to listOf("ルージュ・ザ・バット", "rouge_the_bat"),
        "rouge_the_bat" to listOf("ルージュ・ザ・バット", "rouge_the_bat"),
        "shadow_rouge" to listOf("シャドルー(ソニック)", "shadouge"),
        "shadow_the_hedgehog rouge_the_bat" to listOf("シャドルー(ソニック)", "shadouge"),
        "shadow_sonic" to listOf("ソニシャド", "sonadow"),
        "shadow_the_hedgehog sonic_the_hedgehog" to listOf("ソニシャド", "sonadow"),
        "loona_(helluva_boss)" to listOf("HelluvaBoss Loona"),
        "blitz_(helluva_boss)" to listOf("Blitzo"),
        "millie_(helluva_boss)" to listOf("HelluvaBoss Millie"),
        "moxxie_(helluva_boss)" to listOf("Moxxie"),
        "fizzarolli_(helluva_boss)" to listOf("Fizzarolli"),
        "stolas_(helluva_boss)" to listOf("Stolas", "ストラス"),
        "alastor_(hazbin_hotel)" to listOf("Alastor", "アラスター"),
        "angel_dust" to listOf("AngelDust", "エンジェルダスト"),
        "husk_(hazbin_hotel)" to listOf("HazbinHotel Husk"),
        "lucifer_morningstar_(hazbin_hotel)" to listOf("HazbinHotel Lucifer", "ルシファー(ハズビンホテル)"),
        "yamato_(one_piece)" to listOf("ヤマト(ONEPIECE)", "ヤマト(ワンピース)"),
        "perona_(one_piece)" to listOf("ペローナ"),
        "nami_(one_piece)" to listOf("ONEPIECE ナミ", "ナミ"),
        "vex_lol" to listOf("ヴェックス"),
        "vex_(league_of_legends)" to listOf("ヴェックス"),
        "vex_(league)" to listOf("ヴェックス"),
        "evelynn_(league_of_legends)" to listOf("Evelynn"),
        "v_(cyberpunk_2077)" to listOf("サイバーパンク2077 V"),
        "v_cyberpunk" to listOf("サイバーパンク2077 V"),
        "jax_(the_amazing_digital_circus)" to listOf("TADC Jax", "TheAmazingDigitalCircus Jax"),
        "rias_gremory" to listOf("リアス・グレモリー"),
    )
    private val e621 = mapOf(
        "blitz_(helluva_boss)" to listOf("blitzo_(helluva_boss)"),
        "lucifer_morningstar_(hazbin_hotel)" to listOf("lucifer_(hazbin_hotel)"),
    )

    fun find(source: ArtSource, category: Category): List<String>? {
        val candidates = listOf(category.key.lowercase(), category.tags.lowercase().trim())
        val mapping = when (source) { ArtSource.PIXIV -> pixiv; ArtSource.E621 -> e621; else -> return null }
        return candidates.firstNotNullOfOrNull(mapping::get)
    }
}

internal fun derivedTextQuery(value: String): String = value.split(Regex("\\s+"))
    .filterNot { it.startsWith('-') }
    .joinToString(" ") { it.replace('_', ' ').replace("(", " ").replace(")", " ").trim() }
    .replace(Regex("\\s+"), " ").trim()

internal fun JSONObject.string(name: String): String = optString(name).takeUnless { it == "null" }.orEmpty()
internal fun JSONObject.int(name: String): Int = optInt(name, 0)
internal fun JSONObject.long(name: String): Long = optLong(name, 0)

internal fun JSONObject.epochSeconds(name: String): Long {
    val value = opt(name) ?: return 0
    val numeric = when (value) {
        is Number -> value.toLong()
        is String -> value.toLongOrNull()
        else -> null
    }
    if (numeric != null) return if (numeric > 10_000_000_000L) numeric / 1000 else numeric
    val text = value.toString().trim()
    return runCatching { Instant.parse(text).epochSecond }
        .recoverCatching { OffsetDateTime.parse(text).toEpochSecond() }
        .recoverCatching {
            ZonedDateTime.parse(
                text.replace(Regex("\\s+"), " "),
                DateTimeFormatter.ofPattern("EEE MMM d HH:mm:ss Z yyyy", Locale.US),
            ).toEpochSecond()
        }
        .getOrDefault(0)
}

internal fun parseArrayOrObject(raw: String, objectKey: String): JSONArray {
    val clean = raw.trim()
    if (clean.isBlank() || clean.startsWith('<') || clean == "null" || clean == "{}") return JSONArray()
    return if (clean.startsWith('[')) JSONArray(clean) else JSONObject(clean).optJSONArray(objectKey) ?: JSONArray()
}

internal fun containsAi(tags: String): Boolean = tags.lowercase().split(Regex("[\\s,;#]+"))
    .any { it in AI_TAGS }

internal val NSFW_TAGS = setOf("porn", "sexual", "nudity", "nsfw", "explicit", "r18", "18+")
internal val SENSITIVE_TAGS = setOf("sensitive", "questionable", "graphic-media", "gore")

internal fun ratingFromTags(tags: String): String {
    val values = tags.lowercase().split(Regex("[\\s,;#]+"))
    return when {
        values.any { it in NSFW_TAGS } -> "nsfw"
        values.any { it in SENSITIVE_TAGS } -> "sensitive"
        else -> "sfw"
    }
}
