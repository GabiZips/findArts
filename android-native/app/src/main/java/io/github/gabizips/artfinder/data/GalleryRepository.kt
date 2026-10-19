package io.github.gabizips.artfinder.data

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.GalleryItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import java.io.IOException
import java.util.Locale
import java.util.concurrent.TimeUnit

class GalleryRepository(
    private val context: Context,
    private val settings: SettingsRepository,
    private val client: OkHttpClient = OkHttpClient.Builder().callTimeout(120, TimeUnit.SECONDS).build(),
) {
    suspend fun keep(post: ArtPost, collectionIds: Set<String> = emptySet()): GalleryItem = withContext(Dispatchers.IO) {
        val uid = "${post.source.id}:${post.id}"
        val existing = settings.galleryItem(uid)
        val item = existing?.copy(collectionIds = collectionIds) ?: GalleryItem(
            uid = uid,
            source = post.source.id,
            sourceId = post.id,
            pageUrl = post.pageUrl,
            previewUrl = post.previewUrl,
            originalUrl = post.url,
            artist = post.artist,
            categoryKey = post.categoryKey,
            savedAt = System.currentTimeMillis(),
            rating = post.rating,
            collectionIds = collectionIds,
        )
        settings.addGalleryItem(item)
        item
    }

    suspend fun download(item: GalleryItem): GalleryItem {
        val source = ArtSource.fromId(item.source) ?: error("Fonte desconhecida: ${item.source}")
        return download(
            ArtPost(
                id = item.sourceId,
                source = source,
                url = item.originalUrl.ifBlank { item.previewUrl },
                previewUrl = item.previewUrl.ifBlank { item.originalUrl },
                pageUrl = item.pageUrl,
                artist = item.artist,
                rating = item.rating,
                categoryKey = item.categoryKey,
            ),
        )
    }

    private val transfers = TransferCoordinator(3)

    private fun readable(uri: String): Boolean = try {
        context.contentResolver.openFileDescriptor(Uri.parse(uri), "r")?.use { true }
            ?: throw IOException("Não foi possível verificar a imagem no dispositivo.")
    } catch (_: java.io.FileNotFoundException) {
        false
    }

    suspend fun download(post: ArtPost): GalleryItem = transfers.run("${post.source.id}:${post.id}") {
        withContext(Dispatchers.IO) {
            val existing = settings.galleryItem("${post.source.id}:${post.id}")
            if (existing != null && existing.contentUri.isNotBlank() && readable(existing.contentUri)) {
                return@withContext existing
            }
            val request = Request.Builder().url(post.url).apply {
                if (post.source.id == "pixiv") header("Referer", "https://www.pixiv.net/")
                header("User-Agent", "ArtFinder-Android/0.10.1")
            }.build()
            val staging = java.io.File.createTempFile("artfinder-", ".download", context.cacheDir)
            val coroutineContext = currentCoroutineContext()
            try {
                val contentType = client.newCall(request).useCancellable { response ->
                    if (!response.isSuccessful) throw IOException("Falha ao baixar: HTTP ${response.code}")
                    require(response.body.contentLength() <= MAX_BYTES) { "A imagem excede 100 MB." }
                    response.body.byteStream().use { input ->
                        staging.outputStream().use { output ->
                            copyBounded(input, output, MAX_BYTES.toLong()) { coroutineContext.ensureActive() }
                        }
                    }
                    response.header("Content-Type").orEmpty().substringBefore(';')
                }
                require(staging.length() in 1..MAX_BYTES.toLong()) { "Arquivo de imagem inválido." }
                val signature = staging.inputStream().use { input ->
                    val bytes = ByteArray(12)
                    bytes.copyOf(input.read(bytes).coerceAtLeast(0))
                }
                val mime = supportedMime(contentType, signature)
                val extension = when (mime) { "image/png" -> "png"; "image/webp" -> "webp"; else -> "jpg" }
                val safeId = post.id.replace(Regex("[^a-zA-Z0-9_-]"), "_").take(100)
                val safeSource = post.source.id.lowercase(Locale.ROOT).replace(Regex("[^a-z0-9_-]"), "_")
                val values = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, "${safeSource}_$safeId.$extension")
                    put(MediaStore.Images.Media.MIME_TYPE, mime)
                    put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/ArtFinder")
                    put(MediaStore.Images.Media.IS_PENDING, 1)
                }
                coroutineContext.ensureActive()
                val resolver = context.contentResolver
                val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                    ?: error("O Android não permitiu criar a imagem na galeria.")
                try {
                    resolver.openOutputStream(uri, "w")?.use { output ->
                        staging.inputStream().use { input ->
                            copyBounded(input, output, MAX_BYTES.toLong()) { coroutineContext.ensureActive() }
                        }
                    } ?: error("Não foi possível escrever a imagem.")
                    check(resolver.update(uri, ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) }, null, null) > 0)
                    val item = GalleryItem(
                        uid = "${post.source.id}:${post.id}", contentUri = uri.toString(),
                        source = post.source.id, sourceId = post.id, pageUrl = post.pageUrl,
                        previewUrl = post.previewUrl, originalUrl = post.url,
                        artist = post.artist, categoryKey = post.categoryKey,
                        savedAt = existing?.savedAt ?: System.currentTimeMillis(),
                        rating = post.rating, collectionIds = existing?.collectionIds.orEmpty(),
                    )
                    settings.addGalleryItem(item)
                    item
                } catch (error: Throwable) {
                    runCatching { resolver.delete(uri, null, null) }
                    throw error
                }
            } finally {
                staging.delete()
            }
        }
    }

    suspend fun delete(item: GalleryItem) = transfers.run(item.uid) {
        withContext(Dispatchers.IO) {
            val current = settings.galleryItem(item.uid) ?: return@withContext
            if (current.contentUri.isBlank()) {
                settings.removeGalleryItem(item.uid)
            } else {
                deleteThenForget(
                    deleteFile = {
                        val uri = Uri.parse(current.contentUri)
                        val deleted = context.contentResolver.delete(uri, null, null)
                        // Zero rows is success only when the image is already absent.
                        if (deleted == 0 && !readable(current.contentUri)) 1 else deleted
                    },
                    forget = { settings.removeGalleryItem(item.uid) },
                )
            }
        }
    }

    suspend fun setCollections(item: GalleryItem, collectionIds: Set<String>) =
        settings.setGalleryCollections(item.uid, collectionIds)

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
