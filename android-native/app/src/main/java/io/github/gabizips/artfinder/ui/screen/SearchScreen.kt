package io.github.gabizips.artfinder.ui.screen

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.blur
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
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOptions
import io.github.gabizips.artfinder.model.SettingsSnapshot
import io.github.gabizips.artfinder.ui.component.ZoomableImageViewer
import io.github.gabizips.artfinder.ui.component.CollectionPickerDialog
import io.github.gabizips.artfinder.ui.originalModel
import io.github.gabizips.artfinder.ui.previewModel
import kotlin.math.roundToInt

@Composable
fun SearchScreen(settings: SettingsSnapshot, state: SearchUiState, viewModel: MainViewModel) {
    var categoryExpanded by remember { mutableStateOf(false) }
    var optionsExpanded by rememberSaveable { mutableStateOf(false) }
    var confirmLargeSearch by remember { mutableStateOf(false) }
    var viewerPost by remember { mutableStateOf<ArtPost?>(null) }
    var collectionPost by remember { mutableStateOf<ArtPost?>(null) }
    var draftOptions by remember { mutableStateOf(settings.searchOptions) }
    LaunchedEffect(settings.searchOptions) { draftOptions = settings.searchOptions }
    LaunchedEffect(settings.categories, state.selectedCategory) {
        if (state.selectedCategory == null && settings.categories.isNotEmpty()) viewModel.selectCategory(settings.categories.first().key)
    }
    val selectedCategory = settings.categories.firstOrNull { it.key == state.selectedCategory } ?: settings.categories.firstOrNull()
    val estimate = viewModel.estimateRequests(selectedCategory, state.selectedSources, draftOptions.pages)
    val startSearch = { viewModel.search(draftOptions) }

    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(stringResource(R.string.search_artworks), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            if (settings.categories.isEmpty()) {
                Text(stringResource(R.string.no_categories))
            } else {
                Box {
                    val selected = selectedCategory ?: settings.categories.first()
                    OutlinedButton(onClick = { categoryExpanded = true }, modifier = Modifier.fillMaxWidth()) {
                        Text("${selected.emoji} ${selected.label} · ${selected.group}", modifier = Modifier.weight(1f))
                    }
                    DropdownMenu(expanded = categoryExpanded, onDismissRequest = { categoryExpanded = false }) {
                        settings.categories.forEach { category ->
                            DropdownMenuItem(text = { Text("${category.emoji} ${category.label} · ${category.group}") }, onClick = {
                                viewModel.selectCategory(category.key); categoryExpanded = false
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
            SearchOptionsCard(
                expanded = optionsExpanded,
                options = draftOptions,
                blurNsfw = settings.displayPreferences.blurNsfw,
                estimatedRequests = estimate,
                onExpandedChange = { optionsExpanded = it },
                onBlurNsfwChange = viewModel::setBlurNsfw,
                onOptionsChange = { updated ->
                    draftOptions = updated
                    viewModel.updateSearchOptions(updated)
                },
            )
            if (state.loading) {
                OutlinedButton(onClick = viewModel::cancelSearch, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.cancel_search))
                }
                Text(
                    stringResource(
                        R.string.search_progress_details,
                        state.completedSources, state.totalSources, state.requestCount, state.estimatedRequests,
                    ),
                    style = MaterialTheme.typography.bodySmall,
                )
            } else {
                Button(
                    onClick = {
                        if (draftOptions.pages >= 21) confirmLargeSearch = true else startSearch()
                    },
                    enabled = settings.categories.isNotEmpty() && state.selectedSources.isNotEmpty(),
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(stringResource(R.string.search)) }
            }
            if (state.errors.isNotEmpty()) {
                Text(state.errors.entries.joinToString("\n") { "${it.key.label}: ${it.value}" }, color = MaterialTheme.colorScheme.error)
            }
            if (!state.loading && (state.requestCount > 0 || state.posts.isNotEmpty())) {
                Text(
                    stringResource(R.string.search_summary, state.posts.size, state.requestCount),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        if (state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
        HorizontalDivider()
        if (!state.loading && state.posts.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text(stringResource(R.string.results_placeholder)) }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(220.dp), modifier = Modifier.fillMaxSize(),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.posts, key = { "${it.source.id}:${it.id}" }) { post ->
                    ArtCard(
                        post = post,
                        state = state,
                        blurNsfw = settings.displayPreferences.blurNsfw,
                        viewModel = viewModel,
                        onOpen = { viewerPost = post },
                        onKeep = { collectionPost = post },
                    )
                }
            }
        }
    }

    viewerPost?.let { post ->
        ZoomableImageViewer(
            model = post.originalModel(LocalContext.current),
            contentDescription = post.tags,
            initiallyBlurred = settings.displayPreferences.blurNsfw && post.rating.equals("nsfw", ignoreCase = true),
            onDismiss = { viewerPost = null },
        )
    }

    collectionPost?.let { post ->
        val existing = settings.gallery.firstOrNull { it.uid == "${post.source.id}:${post.id}" }
        CollectionPickerDialog(
            collections = settings.collections,
            initialSelection = existing?.collectionIds.orEmpty(),
            onDismiss = { collectionPost = null },
            onConfirm = { collectionIds ->
                viewModel.keep(post, collectionIds)
                collectionPost = null
            },
        )
    }

    if (confirmLargeSearch) {
        AlertDialog(
            onDismissRequest = { confirmLargeSearch = false },
            title = { Text(stringResource(R.string.large_search_title)) },
            text = { Text(stringResource(R.string.large_search_confirmation, draftOptions.pages, estimate)) },
            confirmButton = {
                TextButton(onClick = { confirmLargeSearch = false; startSearch() }) { Text(stringResource(R.string.continue_search)) }
            },
            dismissButton = { TextButton(onClick = { confirmLargeSearch = false }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun SearchOptionsCard(
    expanded: Boolean,
    options: SearchOptions,
    blurNsfw: Boolean,
    estimatedRequests: Int,
    onExpandedChange: (Boolean) -> Unit,
    onBlurNsfwChange: (Boolean) -> Unit,
    onOptionsChange: (SearchOptions) -> Unit,
) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Row(
                Modifier.fillMaxWidth().clickable { onExpandedChange(!expanded) },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(stringResource(R.string.search_options), fontWeight = FontWeight.Bold)
                    Text(
                        stringResource(R.string.pages_and_requests, options.pages, estimatedRequests),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Icon(if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore, null)
            }
            AnimatedVisibility(expanded) {
                Column(
                    Modifier.padding(top = 10.dp).heightIn(max = 390.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Text(stringResource(R.string.pages_per_source, options.pages), fontWeight = FontWeight.SemiBold)
                    Slider(
                        value = options.pages.toFloat(),
                        onValueChange = { onOptionsChange(options.copy(pages = it.roundToInt().coerceIn(1, 25))) },
                        valueRange = 1f..25f,
                        steps = 23,
                    )
                    SearchWarning(options.pages, estimatedRequests)
                    Text(stringResource(R.string.content_rating), fontWeight = FontWeight.SemiBold)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        item {
                            FilterChip(options.includeSfw, { toggleRating(options, "sfw", onOptionsChange) }, { Text("SFW") })
                        }
                        item {
                            FilterChip(options.includeSensitive, { toggleRating(options, "sensitive", onOptionsChange) }, { Text(stringResource(R.string.sensitive)) })
                        }
                        item {
                            FilterChip(options.includeNsfw, { toggleRating(options, "nsfw", onOptionsChange) }, { Text("NSFW") })
                        }
                    }
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(stringResource(R.string.blur_nsfw), fontWeight = FontWeight.SemiBold)
                            Text(stringResource(R.string.nsfw_blur_notice), style = MaterialTheme.typography.bodySmall)
                        }
                        Switch(checked = blurNsfw, onCheckedChange = onBlurNsfwChange)
                    }
                    Text(stringResource(R.string.period), fontWeight = FontWeight.SemiBold)
                    val periods = listOf(0 to R.string.period_all, 7 to R.string.period_7, 30 to R.string.period_30, 90 to R.string.period_90, 180 to R.string.period_180, 365 to R.string.period_365)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(periods) { (days, label) ->
                            FilterChip(
                                selected = options.periodDays == days,
                                onClick = { onOptionsChange(options.copy(periodDays = days)) },
                                label = { Text(stringResource(label)) },
                            )
                        }
                    }
                    OutlinedTextField(
                        value = options.minScore.takeIf { it > 0 }?.toString().orEmpty(),
                        onValueChange = { value ->
                            val clean = value.filter(Char::isDigit).take(7)
                            onOptionsChange(options.copy(minScore = clean.toIntOrNull() ?: 0))
                        },
                        label = { Text(stringResource(R.string.minimum_score)) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text(stringResource(R.string.ai_filter_mandatory), style = MaterialTheme.typography.bodySmall)
                    Text(stringResource(R.string.any_resolution), style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

private fun toggleRating(options: SearchOptions, rating: String, onChange: (SearchOptions) -> Unit) {
    val activeCount = listOf(options.includeSfw, options.includeSensitive, options.includeNsfw).count { it }
    val currentlyActive = when (rating) {
        "sfw" -> options.includeSfw
        "sensitive" -> options.includeSensitive
        else -> options.includeNsfw
    }
    if (currentlyActive && activeCount == 1) return
    onChange(
        when (rating) {
            "sfw" -> options.copy(includeSfw = !options.includeSfw)
            "sensitive" -> options.copy(includeSensitive = !options.includeSensitive)
            else -> options.copy(includeNsfw = !options.includeNsfw)
        },
    )
}

@Composable
private fun SearchWarning(pages: Int, requests: Int) {
    val (message, color) = when (pages) {
        in 1..5 -> R.string.search_size_normal to MaterialTheme.colorScheme.onSurfaceVariant
        in 6..10 -> R.string.search_size_medium to Color(0xFFFBC02D)
        in 11..20 -> R.string.search_size_large to Color(0xFFFF8F00)
        else -> R.string.search_size_very_large to MaterialTheme.colorScheme.error
    }
    Text(stringResource(message, requests), color = color, style = MaterialTheme.typography.bodySmall)
}

@Composable
private fun ArtCard(
    post: ArtPost,
    state: SearchUiState,
    blurNsfw: Boolean,
    viewModel: MainViewModel,
    onOpen: () -> Unit,
    onKeep: () -> Unit,
) {
    val context = LocalContext.current
    val uid = "${post.source.id}:${post.id}"
    var nsfwRevealed by rememberSaveable(uid) { mutableStateOf(false) }
    val hiddenNsfw = blurNsfw && post.rating.equals("nsfw", ignoreCase = true) && !nsfwRevealed
    ElevatedCard(Modifier.fillMaxWidth()) {
        Box(
            Modifier.fillMaxWidth().height(280.dp).clickable {
                if (!hiddenNsfw) onOpen()
            },
        ) {
            AsyncImage(
                model = post.previewModel(context), contentDescription = post.tags,
                modifier = Modifier.fillMaxSize().blur(if (hiddenNsfw) 24.dp else 0.dp),
                contentScale = ContentScale.Crop,
            )
            if (hiddenNsfw) {
                Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.42f)), contentAlignment = Alignment.Center) {
                    Button(onClick = { nsfwRevealed = true }) {
                        Text(stringResource(R.string.show_nsfw), color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        Column(Modifier.padding(10.dp)) {
            Text(post.source.label, fontWeight = FontWeight.Bold)
            Text(post.artist.ifBlank { stringResource(R.string.unknown_artist) }, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("★ ${post.score} · ${post.width}×${post.height}", style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(4.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                if (post.pageUrl.isNotBlank()) IconButton(onClick = {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(post.pageUrl)))
                }) { Icon(Icons.AutoMirrored.Outlined.OpenInNew, stringResource(R.string.open_source)) }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onKeep, enabled = uid !in state.saving, modifier = Modifier.weight(1f)) {
                    Icon(Icons.Outlined.BookmarkBorder, null)
                    Spacer(Modifier.width(4.dp))
                    Text(stringResource(R.string.keep))
                }
                Button(onClick = { viewModel.download(post) }, enabled = uid !in state.saving, modifier = Modifier.weight(1f)) {
                    if (uid in state.saving) CircularProgressIndicator(Modifier.width(20.dp))
                    else {
                        Icon(Icons.Outlined.Download, null)
                        Spacer(Modifier.width(4.dp))
                        Text(stringResource(R.string.download))
                    }
                }
            }
        }
    }
}
