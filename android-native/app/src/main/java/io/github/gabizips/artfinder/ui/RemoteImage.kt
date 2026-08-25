package io.github.gabizips.artfinder.ui

import android.content.Context
import coil3.network.NetworkHeaders
import coil3.network.httpHeaders
import coil3.request.ImageRequest
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.GalleryItem

fun ArtPost.previewModel(context: Context): ImageRequest = ImageRequest.Builder(context)
    .data(previewUrl)
    .apply {
        if (source.id == "pixiv") {
            httpHeaders(
                NetworkHeaders.Builder()
                    .set("Referer", "https://www.pixiv.net/")
                    .build(),
            )
        }
    }
    .build()

fun ArtPost.originalModel(context: Context): ImageRequest = ImageRequest.Builder(context)
    .data(url)
    .apply {
        if (source.id == "pixiv") {
            httpHeaders(
                NetworkHeaders.Builder()
                    .set("Referer", "https://www.pixiv.net/")
                    .build(),
            )
        }
    }
    .build()

fun GalleryItem.imageModel(context: Context): Any {
    if (contentUri.isNotBlank()) return android.net.Uri.parse(contentUri)
    return ImageRequest.Builder(context)
        .data(previewUrl.ifBlank { originalUrl })
        .apply {
            if (source == "pixiv") {
                httpHeaders(
                    NetworkHeaders.Builder()
                        .set("Referer", "https://www.pixiv.net/")
                        .build(),
                )
            }
        }
        .build()
}

fun GalleryItem.originalModel(context: Context): Any {
    if (contentUri.isNotBlank()) return android.net.Uri.parse(contentUri)
    return ImageRequest.Builder(context)
        .data(originalUrl.ifBlank { previewUrl })
        .apply {
            if (source == "pixiv") {
                httpHeaders(
                    NetworkHeaders.Builder()
                        .set("Referer", "https://www.pixiv.net/")
                        .build(),
                )
            }
        }
        .build()
}
