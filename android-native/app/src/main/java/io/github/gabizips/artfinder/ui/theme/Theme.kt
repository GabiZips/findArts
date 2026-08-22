package io.github.gabizips.artfinder.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColors = darkColorScheme(
    primary = Color(0xFF9C6CFF), secondary = Color(0xFF20D779),
    background = Color(0xFF0F0F14), surface = Color(0xFF17171F),
    surfaceVariant = Color(0xFF242430), onBackground = Color(0xFFF2EEF9),
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF6D39D7), secondary = Color(0xFF087A3C),
    background = Color(0xFFF9F7FC), surface = Color.White,
)

@Composable
fun ArtFinderTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors, content = content)
}
