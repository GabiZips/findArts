package io.github.gabizips.artfinder.ui.component

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import io.github.gabizips.artfinder.R

internal fun shouldHideArtwork(rating: String, hideNsfw: Boolean, revealed: Boolean = false): Boolean =
    hideNsfw && !revealed && rating.trim().lowercase() in setOf("nsfw", "explicit", "e", "sensitive", "questionable", "q", "s")

/** Hidden artwork is not composed or loaded; protection works from API 29 without platform blur. */
@Composable
internal fun ProtectedArtwork(
    hidden: Boolean,
    modifier: Modifier = Modifier,
    onReveal: (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    Box(modifier) {
        if (hidden) {
            Box(
                Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceContainerHighest.copy(alpha = 1f)),
                contentAlignment = Alignment.Center,
            ) {
                if (onReveal != null) Button(onClick = onReveal) { Text(stringResource(R.string.show_nsfw)) }
            }
        } else {
            content()
        }
    }
}
