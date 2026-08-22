package io.github.gabizips.artfinder.data

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.GalleryItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.Locale

class GalleryRepository(
    private val context: Context,
    private val settings: SettingsRepository,
    private val client: OkHttpClient = OkHttpClient(),
) {
    suspend fun save(post: ArtPost): GalleryItem = withContext(Dispatchers.IO) {
        val request = Request.Builder().url(post.url).apply {
            if (post.source.id == "pixiv") header("Referer", "https://www.pixiv.net/")
            header("User-Agent", "ArtFinder-Android/0.6.0")
        }.build()
        val downloaded = client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Falha ao baixar: HTTP ${response.code}")
            val body = response.body
            require(body.contentLength() <= MAX_BYTES || body.contentLength() < 0) { "A imagem excede 100 MB." }
            val bytes = body.byteStream().use { input ->
                val output = ByteArrayOutputStream(body.contentLength().coerceIn(0, 4L * 1024 * 1024).toInt())
                val buffer = ByteArray(16 * 1024)
                var total = 0
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    total += count
                    require(total <= MAX_BYTES) { "A imagem excede 100 MB." }
                    output.write(buffer, 0, count)
                }
                output.toByteArray()
            }
            require(bytes.size in 1..MAX_BYTES) { "Arquivo de imagem inválido." }
            bytes to response.header("Content-Type").orEmpty().substringBefore(';')
        }
        val mime = supportedMime(downloaded.second, downloaded.first)
        val extension = when (mime) { "image/png" -> "png"; "image/webp" -> "webp"; else -> "jpg" }
        val safeSource = post.source.id.lowercase(Locale.ROOT).replace(Regex("[^a-z0-9_-]"), "_")
        val safeId = post.id.replace(Regex("[^a-zA-Z0-9_-]"), "_").take(100)
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, "${safeSource}_${safeId}.$extension")
            put(MediaStore.Images.Media.MIME_TYPE, mime)
            put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/ArtFinder")
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }
        val resolver = context.contentResolver
        val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            ?: error("O Android não permitiu criar a imagem na galeria.")
        try {
            resolver.openOutputStream(uri, "w")?.use { it.write(downloaded.first) }
                ?: error("Não foi possível escrever a imagem.")
            resolver.update(uri, ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) }, null, null)
        } catch (error: Throwable) {
            resolver.delete(uri, null, null)
            throw error
        }
        val item = GalleryItem(
            uid = "${post.source.id}:${post.id}", contentUri = uri.toString(),
            source = post.source.id, sourceId = post.id, pageUrl = post.pageUrl,
            artist = post.artist, categoryKey = post.categoryKey, savedAt = System.currentTimeMillis(),
            rating = post.rating,
        )
        settings.addGalleryItem(item)
        item
    }

    suspend fun delete(item: GalleryItem) = withContext(Dispatchers.IO) {
        val uri = Uri.parse(item.contentUri)
        runCatching { context.contentResolver.delete(uri, null, null) }
        settings.removeGalleryItem(item.uid)
    }

    private fun supportedMime(header: String, bytes: ByteArray): String {
        val detected = when {
            bytes.size >= 8 && bytes.copyOfRange(0, 8).contentEquals(PNG_SIGNATURE) -> "image/png"
            bytes.size >= 12 && bytes.copyOfRange(0, 4).toString(Charsets.US_ASCII) == "RIFF" &&
                bytes.copyOfRange(8, 12).toString(Charsets.US_ASCII) == "WEBP" -> "image/webp"
            bytes.size >= 3 && bytes[0] == 0xFF.toByte() && bytes[1] == 0xD8.toByte() && bytes[2] == 0xFF.toByte() -> "image/jpeg"
            else -> null
        }
        require(detected != null) { "O arquivo recebido não é uma imagem JPEG, PNG ou WebP válida." }
        require(header.isBlank() || header.startsWith("image/") || header == "application/octet-stream") {
            "A fonte retornou um tipo de arquivo inválido."
        }
        return detected
    }

    private companion object {
        const val MAX_BYTES = 100 * 1024 * 1024
        val PNG_SIGNATURE = byteArrayOf(0x89.toByte(), 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
    }
}
