package io.github.gabizips.artfinder.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable

@Composable
fun ArtFinderTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) ArtFinderDarkColors else ArtFinderLightColors,
        typography = ArtFinderTypography,
        shapes = ArtFinderShapes,
        content = content,
    )
}
