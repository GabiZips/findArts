package io.github.gabizips.artfinder.ui

import android.content.Context
import coil3.network.NetworkHeaders
import coil3.network.httpHeaders
import coil3.request.ImageRequest
import io.github.gabizips.artfinder.model.ArtPost

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
