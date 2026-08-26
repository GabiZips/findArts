package io.github.gabizips.artfinder.ui.component

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil3.compose.AsyncImage
import io.github.gabizips.artfinder.R

data class ViewerImage(
    val key: String,
    val model: Any,
    val contentDescription: String,
    val title: String,
    val subtitle: String,
    val initiallyBlurred: Boolean,
)

@Composable
fun ZoomableImageViewer(
    images: List<ViewerImage>,
    initialIndex: Int,
    onDismiss: () -> Unit,
) {
    if (images.isEmpty()) return
    val safeInitialIndex = initialIndex.coerceIn(images.indices)
    val pagerState = rememberPagerState(initialPage = safeInitialIndex) { images.size }
    var controlsVisible by remember { mutableStateOf(true) }
    var currentScale by remember { mutableFloatStateOf(1f) }

    LaunchedEffect(pagerState.currentPage) {
        currentScale = 1f
        controlsVisible = true
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        Box(Modifier.fillMaxSize().background(Color.Black)) {
            HorizontalPager(
                state = pagerState,
                modifier = Modifier.fillMaxSize(),
                userScrollEnabled = images.size > 1 && currentScale <= 1.01f,
                beyondViewportPageCount = 1,
                key = { images[it].key },
            ) { page ->
                ZoomableImagePage(
                    image = images[page],
                    active = page == pagerState.currentPage,
                    onScaleChanged = { currentScale = it },
                    onToggleControls = { controlsVisible = !controlsVisible },
                )
            }

            AnimatedVisibility(
                visible = controlsVisible,
                enter = fadeIn(),
                exit = fadeOut(),
                modifier = Modifier.fillMaxSize(),
            ) {
                ViewerControls(
                    image = images[pagerState.currentPage],
                    currentPage = pagerState.currentPage,
                    pageCount = images.size,
                    scale = currentScale,
                    onDismiss = onDismiss,
                )
            }
        }
    }
}

@Composable
private fun ZoomableImagePage(
    image: ViewerImage,
    active: Boolean,
    onScaleChanged: (Float) -> Unit,
    onToggleControls: () -> Unit,
) {
    var scale by remember(image.key) { mutableFloatStateOf(1f) }
    var offset by remember(image.key) { mutableStateOf(Offset.Zero) }
    var revealed by remember(image.key) { mutableStateOf(!image.initiallyBlurred) }

    fun updateScale(next: Float) {
        scale = next.coerceIn(1f, 6f)
        if (scale == 1f) offset = Offset.Zero
        if (active) onScaleChanged(scale)
    }
    fun reset() {
        offset = Offset.Zero
        updateScale(1f)
    }

    LaunchedEffect(active) {
        if (active) onScaleChanged(scale)
    }

    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        AsyncImage(
            model = image.model,
            contentDescription = image.contentDescription,
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .fillMaxSize()
                .graphicsLayer(
                    scaleX = scale,
                    scaleY = scale,
                    translationX = offset.x,
                    translationY = offset.y,
                )
                .combinedClickable(
                    enabled = revealed,
                    onClick = onToggleControls,
                    onDoubleClick = { if (scale > 1f) reset() else updateScale(2.5f) },
                )
                .pointerInput(image.key, revealed) {
                    if (!revealed) return@pointerInput
                    awaitEachGesture {
                        awaitFirstDown(requireUnconsumed = false)
                        do {
                            val event = awaitPointerEvent()
                            val multiTouch = event.changes.count { it.pressed } >= 2
                            if (multiTouch || scale > 1.01f) {
                                val nextScale = (scale * event.calculateZoom()).coerceIn(1f, 6f)
                                scale = nextScale
                                offset = if (nextScale <= 1.01f) Offset.Zero else offset + event.calculatePan()
                                if (active) onScaleChanged(scale)
                                event.changes.forEach { it.consume() }
                            }
                        } while (event.changes.any { it.pressed })
                    }
                }
                .blur(if (revealed) 0.dp else 28.dp),
        )
        if (!revealed) {
            Box(
                Modifier.fillMaxSize().background(Color.Black.copy(alpha = .5f)),
                contentAlignment = Alignment.Center,
            ) {
                Button(onClick = { revealed = true }) { Text(stringResource(R.string.show_nsfw)) }
            }
        }
    }
}

@Composable
private fun ViewerControls(
    image: ViewerImage,
    currentPage: Int,
    pageCount: Int,
    scale: Float,
    onDismiss: () -> Unit,
) {
    Box(
        Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    0f to Color.Black.copy(alpha = .76f),
                    .22f to Color.Transparent,
                    .72f to Color.Transparent,
                    1f to Color.Black.copy(alpha = .82f),
                ),
            )
            .windowInsetsPadding(WindowInsets.safeDrawing),
    ) {
        Row(
            Modifier.fillMaxWidth().align(Alignment.TopCenter).padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Surface(color = Color.White.copy(alpha = .14f), contentColor = Color.White, shape = CircleShape) {
                Text(
                    stringResource(R.string.viewer_position, currentPage + 1, pageCount),
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                    style = MaterialTheme.typography.labelLarge,
                )
            }
            Spacer(Modifier.weight(1f))
            Surface(color = Color.White.copy(alpha = .14f), contentColor = Color.White, shape = CircleShape) {
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Outlined.Close, stringResource(R.string.close))
                }
            }
        }

        Column(
            Modifier.fillMaxWidth().align(Alignment.BottomCenter).padding(horizontal = 14.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (pageCount > 1 && scale <= 1.01f) {
                Text(
                    stringResource(R.string.swipe_for_next),
                    color = Color.White.copy(alpha = .78f),
                    style = MaterialTheme.typography.labelMedium,
                )
            }
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = Color(0xFF17151F).copy(alpha = .9f),
                contentColor = Color.White,
                shape = RoundedCornerShape(24.dp),
            ) {
                Row(
                    Modifier.padding(horizontal = 16.dp, vertical = 11.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            image.title,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            image.subtitle,
                            color = Color.White.copy(alpha = .68f),
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Surface(color = Color.White.copy(alpha = .1f), shape = CircleShape) {
                        Text(
                            "${(scale * 100).toInt()}%",
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                            style = MaterialTheme.typography.labelMedium,
                        )
                    }
                }
            }
            Spacer(Modifier.height(2.dp))
        }
    }
}
