package io.github.gabizips.artfinder.ui.screen

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.model.GalleryItem

@Composable
fun GalleryScreen(items: List<GalleryItem>, viewModel: MainViewModel) {
    val context = LocalContext.current
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(16.dp)) {
            Text(stringResource(R.string.gallery), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(stringResource(R.string.gallery_path))
        }
        if (items.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text(stringResource(R.string.no_saved_images)) }
        } else LazyVerticalGrid(
            columns = GridCells.Adaptive(160.dp), contentPadding = androidx.compose.foundation.layout.PaddingValues(8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(items, key = GalleryItem::uid) { item ->
                var nsfwRevealed by rememberSaveable(item.uid) { mutableStateOf(false) }
                val hiddenNsfw = item.rating.equals("nsfw", ignoreCase = true) && !nsfwRevealed
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Box(
                        Modifier.fillMaxWidth().height(210.dp).clickable {
                            if (hiddenNsfw) nsfwRevealed = true
                            else context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(item.contentUri)).setDataAndType(Uri.parse(item.contentUri), "image/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
                        },
                    ) {
                        AsyncImage(
                            model = Uri.parse(item.contentUri), contentDescription = item.artist,
                            modifier = Modifier.fillMaxSize().blur(if (hiddenNsfw) 24.dp else 0.dp),
                            contentScale = ContentScale.Crop,
                        )
                        if (hiddenNsfw) {
                            Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.42f)), contentAlignment = Alignment.Center) {
                                Text(stringResource(R.string.tap_reveal_nsfw), color = Color.White, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                    Column(Modifier.padding(10.dp)) {
                        Text(item.artist.ifBlank { item.source }, maxLines = 1, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.Bold)
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                            if (item.pageUrl.isNotBlank()) IconButton(onClick = {
                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(item.pageUrl)))
                            }) { Icon(Icons.AutoMirrored.Outlined.OpenInNew, stringResource(R.string.open_source)) }
                            IconButton(onClick = { viewModel.delete(item) }) { Icon(Icons.Outlined.Delete, stringResource(R.string.delete)) }
                        }
                    }
                }
            }
        }
    }
}
