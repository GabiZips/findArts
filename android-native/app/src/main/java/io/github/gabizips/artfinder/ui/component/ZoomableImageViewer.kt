package io.github.gabizips.artfinder.ui.component

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Remove
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil3.compose.AsyncImage
import io.github.gabizips.artfinder.R

@Composable
fun ZoomableImageViewer(
    model: Any,
    contentDescription: String,
    initiallyBlurred: Boolean,
    onDismiss: () -> Unit,
) {
    var scale by remember(model) { mutableFloatStateOf(1f) }
    var offset by remember(model) { mutableStateOf(Offset.Zero) }
    var revealed by remember(model) { mutableStateOf(!initiallyBlurred) }
    val transformState = rememberTransformableState { _, zoomChange, panChange, _ ->
        val nextScale = (scale * zoomChange).coerceIn(1f, 6f)
        scale = nextScale
        offset = if (nextScale == 1f) Offset.Zero else offset + panChange
    }
    fun reset() {
        scale = 1f
        offset = Offset.Zero
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        Surface(color = Color.Black.copy(alpha = .97f), modifier = Modifier.fillMaxSize()) {
            Box(Modifier.fillMaxSize()) {
                AsyncImage(
                    model = model,
                    contentDescription = contentDescription,
                    contentScale = ContentScale.Fit,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(vertical = 64.dp)
                        .graphicsLayer(
                            scaleX = scale,
                            scaleY = scale,
                            translationX = offset.x,
                            translationY = offset.y,
                        )
                        .pointerInput(revealed) {
                            if (revealed) {
                                detectTapGestures(
                                    onDoubleTap = {
                                        if (scale > 1f) reset() else scale = 2.5f
                                    },
                                )
                            }
                        }
                        .transformable(transformState)
                        .blur(if (revealed) 0.dp else 28.dp),
                )
                if (!revealed) {
                    Box(
                        Modifier.fillMaxSize().background(Color.Black.copy(alpha = .32f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Button(onClick = { revealed = true }) { Text(stringResource(R.string.show_nsfw)) }
                    }
                }
                Box(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing)) {
                    IconButton(onClick = onDismiss, modifier = Modifier.align(Alignment.TopEnd).padding(12.dp)) {
                        Icon(Icons.Outlined.Close, stringResource(R.string.close), tint = Color.White)
                    }
                    Surface(
                        modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp),
                        color = Color.Black.copy(alpha = .72f),
                        contentColor = Color.White,
                        shape = androidx.compose.foundation.shape.CircleShape,
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            IconButton(onClick = {
                                scale = (scale - .5f).coerceAtLeast(1f)
                                if (scale == 1f) offset = Offset.Zero
                            }) { Icon(Icons.Outlined.Remove, stringResource(R.string.zoom_out)) }
                            Button(onClick = { reset() }) { Text("${(scale * 100).toInt()}%") }
                            IconButton(onClick = { scale = (scale + .5f).coerceAtMost(6f) }) {
                                Icon(Icons.Outlined.Add, stringResource(R.string.zoom_in))
                            }
                        }
                    }
                }
            }
        }
    }
}
