package io.github.gabizips.artfinder.ui.screen

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.SearchUiState
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.SettingsSnapshot
import io.github.gabizips.artfinder.ui.previewModel

@Composable
fun SearchScreen(settings: SettingsSnapshot, state: SearchUiState, viewModel: MainViewModel) {
    var expanded by remember { mutableStateOf(false) }
    LaunchedEffect(settings.categories, state.selectedCategory) {
        if (state.selectedCategory == null && settings.categories.isNotEmpty()) viewModel.selectCategory(settings.categories.first().key)
    }
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(stringResource(R.string.search_artworks), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            if (settings.categories.isEmpty()) {
                Text(stringResource(R.string.no_categories))
            } else {
                Box {
                    val selected = settings.categories.firstOrNull { it.key == state.selectedCategory } ?: settings.categories.first()
                    OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
                        Text("${selected.emoji} ${selected.label} · ${selected.group}", modifier = Modifier.weight(1f))
                    }
                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        settings.categories.forEach { category ->
                            DropdownMenuItem(text = { Text("${category.emoji} ${category.label} · ${category.group}") }, onClick = {
                                viewModel.selectCategory(category.key); expanded = false
                            })
                        }
                    }
                }
            }
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(ArtSource.entries) { source ->
                    FilterChip(
                        selected = source in state.selectedSources,
                        onClick = { viewModel.toggleSource(source) },
                        label = { Text(source.label) },
                    )
                }
            }
            Button(
                onClick = { viewModel.search() }, enabled = !state.loading && settings.categories.isNotEmpty(),
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (state.loading) stringResource(R.string.searching) else stringResource(R.string.search)) }
            state.message?.let {
                Card(Modifier.fillMaxWidth()) { Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(it, Modifier.weight(1f)); TextButton(onClick = viewModel::clearMessages) { Text("OK") }
                } }
            }
            if (state.errors.isNotEmpty()) {
                Text(state.errors.entries.joinToString("\n") { "${it.key.label}: ${it.value}" }, color = MaterialTheme.colorScheme.error)
            }
        }
        if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
        HorizontalDivider()
        if (!state.loading && state.posts.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text(stringResource(R.string.results_placeholder)) }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(160.dp), modifier = Modifier.fillMaxSize(),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp),
            ) { items(state.posts, key = { "${it.source.id}:${it.id}" }) { post -> ArtCard(post, state, viewModel) } }
        }
    }
}

@Composable
private fun ArtCard(post: ArtPost, state: SearchUiState, viewModel: MainViewModel) {
    val context = LocalContext.current
    val uid = "${post.source.id}:${post.id}"
    ElevatedCard(Modifier.fillMaxWidth()) {
        AsyncImage(
            model = post.previewModel(context), contentDescription = post.tags,
            modifier = Modifier.fillMaxWidth().height(210.dp).clickable {
                if (post.pageUrl.isNotBlank()) context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(post.pageUrl)))
            },
            contentScale = ContentScale.Crop,
        )
        Column(Modifier.padding(10.dp)) {
            Text(post.source.label, fontWeight = FontWeight.Bold)
            Text(post.artist.ifBlank { stringResource(R.string.unknown_artist) }, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("★ ${post.score} · ${post.width}×${post.height}", style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(4.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                if (post.pageUrl.isNotBlank()) IconButton(onClick = {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(post.pageUrl)))
                }) { Icon(Icons.AutoMirrored.Outlined.OpenInNew, stringResource(R.string.open_source)) }
                Spacer(Modifier.width(4.dp))
                IconButton(onClick = { viewModel.save(post) }, enabled = uid !in state.saving) {
                    if (uid in state.saving) CircularProgressIndicator(Modifier.width(20.dp))
                    else Icon(Icons.Outlined.Download, stringResource(R.string.save_to_gallery))
                }
            }
        }
    }
}
