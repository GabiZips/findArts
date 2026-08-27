package io.github.gabizips.artfinder.ui.screen

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.material.icons.outlined.ArrowDropDown
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ImageSearch
import androidx.compose.material.icons.outlined.Tag
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Surface
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.SearchUiState
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOptions
import io.github.gabizips.artfinder.model.SettingsSnapshot
import io.github.gabizips.artfinder.ui.component.ArtworkPreview
import io.github.gabizips.artfinder.ui.component.ArtFinderPanel
import io.github.gabizips.artfinder.ui.component.ArtFinderPill
import io.github.gabizips.artfinder.ui.component.ArtFinderBackdrop
import io.github.gabizips.artfinder.ui.component.ArtFinderSecondaryButton
import io.github.gabizips.artfinder.ui.component.CollectionPickerDialog
import io.github.gabizips.artfinder.ui.component.EmptyState
import io.github.gabizips.artfinder.ui.component.SectionHeader
import io.github.gabizips.artfinder.ui.component.ViewerImage
import io.github.gabizips.artfinder.ui.component.ZoomableImageViewer
import io.github.gabizips.artfinder.ui.originalModel
import io.github.gabizips.artfinder.ui.previewModel
import kotlin.math.roundToInt

@Composable
fun SearchScreen(
    settings: SettingsSnapshot,
    state: SearchUiState,
    viewModel: MainViewModel,
    onManageTags: () -> Unit,
) {
    var categoryExpanded by remember { mutableStateOf(false) }
    var optionsExpanded by rememberSaveable { mutableStateOf(false) }
    var controlsExpanded by rememberSaveable { mutableStateOf(state.posts.isEmpty()) }
    var confirmLargeSearch by remember { mutableStateOf(false) }
    var viewerUid by rememberSaveable { mutableStateOf<String?>(null) }
    var collectionPost by remember { mutableStateOf<ArtPost?>(null) }
    var draftOptions by remember { mutableStateOf(settings.searchOptions) }
    val context = LocalContext.current
    val unknownArtist = stringResource(R.string.unknown_artist)
    LaunchedEffect(settings.searchOptions) { draftOptions = settings.searchOptions }
    LaunchedEffect(state.posts.size) {
        if (state.posts.isNotEmpty()) controlsExpanded = false
    }
    LaunchedEffect(settings.categories, state.selectedCategory) {
        if (state.selectedCategory == null && settings.categories.isNotEmpty()) viewModel.selectCategory(settings.categories.first().key)
    }
    val selectedCategory = settings.categories.firstOrNull { it.key == state.selectedCategory } ?: settings.categories.firstOrNull()
    val estimate = viewModel.estimateRequests(selectedCategory, state.selectedSources, draftOptions.pages)
    val startSearch = {
        controlsExpanded = false
        viewModel.search(draftOptions)
    }

    ArtFinderBackdrop {
        Column(Modifier.fillMaxSize()) {
            AnimatedVisibility(
                visible = controlsExpanded || (state.posts.isEmpty() && !state.loading),
                enter = fadeIn(),
                exit = fadeOut() + shrinkVertically(),
            ) {
                Column(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SearchHero(
                        canCollapse = state.posts.isNotEmpty(),
                        onCollapse = { controlsExpanded = false },
                    )
            if (settings.categories.isEmpty()) {
                EmptyState(
                    icon = Icons.Outlined.Tag,
                    title = stringResource(R.string.no_categories_title),
                    description = stringResource(R.string.no_categories),
                    actionLabel = stringResource(R.string.manage_tags),
                    onAction = onManageTags,
                    modifier = Modifier.fillMaxWidth(),
                )
            } else {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.surfaceContainer.copy(alpha = .94f),
                    shape = MaterialTheme.shapes.extraLarge,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = .18f)),
                    shadowElevation = 2.dp,
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Box {
                    val selected = selectedCategory ?: settings.categories.first()
                    Surface(
                        modifier = Modifier.fillMaxWidth().clickable { categoryExpanded = true },
                        shape = MaterialTheme.shapes.large,
                        color = MaterialTheme.colorScheme.surfaceContainerHighest,
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    ) {
                        Row(
                            Modifier.padding(horizontal = 14.dp, vertical = 13.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(selected.emoji, style = MaterialTheme.typography.titleLarge)
                            Column(Modifier.weight(1f).padding(horizontal = 10.dp)) {
                                Text(selected.label, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                Text(selected.group, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Icon(Icons.Outlined.ArrowDropDown, contentDescription = null)
                        }
                    }
                    DropdownMenu(expanded = categoryExpanded, onDismissRequest = { categoryExpanded = false }) {
                        settings.categories.forEach { category ->
                            DropdownMenuItem(text = { Text("${category.emoji} ${category.label} · ${category.group}") }, onClick = {
                                viewModel.selectCategory(category.key); categoryExpanded = false
                            })
                        }
                    }
                }
                SectionHeader(
                    title = stringResource(R.string.source_selection),
                    supportingText = stringResource(
                        R.string.selected_sources,
                        state.selectedSources.size,
                        ArtSource.entries.size,
                    ),
                )
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(ArtSource.entries) { source ->
                        val selected = source in state.selectedSources
                        ArtFinderPill(
                            selected = selected,
                            onClick = { viewModel.toggleSource(source) },
                            label = source.label,
                            icon = if (selected) Icons.Outlined.Check else null,
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
                    Surface(
                        color = MaterialTheme.colorScheme.secondaryContainer,
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                stringResource(
                                    R.string.search_progress_details,
                                    state.completedSources,
                                    state.totalSources,
                                    state.requestCount,
                                    state.estimatedRequests,
                                ),
                                color = MaterialTheme.colorScheme.onSecondaryContainer,
                                style = MaterialTheme.typography.bodySmall,
                            )
                            OutlinedButton(onClick = viewModel::cancelSearch, modifier = Modifier.fillMaxWidth()) {
                                Text(stringResource(R.string.cancel_search))
                            }
                        }
                    }
                } else {
                    GradientSearchButton(
                        onClick = {
                            if (draftOptions.pages >= 21) confirmLargeSearch = true else startSearch()
                        },
                        enabled = state.selectedSources.isNotEmpty(),
                    )
                }
                if (state.errors.isNotEmpty()) {
                    Surface(
                        color = MaterialTheme.colorScheme.errorContainer,
                        contentColor = MaterialTheme.colorScheme.onErrorContainer,
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Text(
                            state.errors.entries.joinToString("\n") { "${it.key.label}: ${it.value}" },
                            modifier = Modifier.padding(12.dp),
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
                    }
                }
            }
                }
            }
            if (settings.categories.isNotEmpty() && !controlsExpanded && (state.loading || state.posts.isNotEmpty())) {
                CompactSearchBar(
                    selectedCategory = selectedCategory,
                    state = state,
                    onEdit = { controlsExpanded = true },
                    onCancel = viewModel::cancelSearch,
                )
            }
            if (settings.categories.isNotEmpty() && state.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
        if (settings.categories.isNotEmpty() && !state.loading && state.posts.isEmpty()) {
            EmptyState(
                icon = Icons.Outlined.ImageSearch,
                title = stringResource(R.string.results_placeholder_title),
                description = stringResource(R.string.results_placeholder),
                modifier = Modifier.weight(1f).fillMaxWidth(),
            )
        } else if (state.posts.isNotEmpty()) {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(220.dp), modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(state.posts, key = { "${it.source.id}:${it.id}" }) { post ->
                    ArtCard(
                        post = post,
                        state = state,
                        blurNsfw = settings.displayPreferences.blurNsfw,
                        viewModel = viewModel,
                        onOpen = { viewerUid = "${post.source.id}:${post.id}" },
                        onKeep = { collectionPost = post },
                    )
                }
            }
            }
        }
    }

    viewerUid?.let { uid ->
        val viewerImages = state.posts.map { post ->
            ViewerImage(
                key = "${post.source.id}:${post.id}",
                model = post.originalModel(context),
                contentDescription = post.tags,
                title = post.artist.ifBlank { unknownArtist },
                subtitle = "${post.source.label} · ${post.width}×${post.height}",
                initiallyBlurred = settings.displayPreferences.blurNsfw && post.rating.equals("nsfw", ignoreCase = true),
            )
        }
        val initialIndex = viewerImages.indexOfFirst { it.key == uid }
        if (initialIndex >= 0) {
            ZoomableImageViewer(
                images = viewerImages,
                initialIndex = initialIndex,
                onDismiss = { viewerUid = null },
            )
        } else {
            LaunchedEffect(uid) { viewerUid = null }
        }
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
private fun SearchHero(canCollapse: Boolean, onCollapse: () -> Unit) {
    Row(
        Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            Modifier
                .size(48.dp)
                .clip(MaterialTheme.shapes.large)
                .background(
                    Brush.linearGradient(
                        listOf(MaterialTheme.colorScheme.primary, MaterialTheme.colorScheme.tertiary),
                    ),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Outlined.ImageSearch, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimary)
        }
        Column(Modifier.weight(1f)) {
            Text(
                stringResource(R.string.app_name).uppercase(),
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(stringResource(R.string.search_artworks), style = MaterialTheme.typography.headlineSmall)
        }
        if (canCollapse) {
            IconButton(onClick = onCollapse) {
                Icon(Icons.Outlined.ExpandLess, stringResource(R.string.hide_search))
            }
        }
    }
}

@Composable
private fun GradientSearchButton(enabled: Boolean, onClick: () -> Unit) {
    val colors = if (enabled) {
        listOf(MaterialTheme.colorScheme.primary, MaterialTheme.colorScheme.tertiary)
    } else {
        listOf(MaterialTheme.colorScheme.surfaceVariant, MaterialTheme.colorScheme.surfaceVariant)
    }
    Box(
        Modifier
            .fillMaxWidth()
            .height(56.dp)
            .clip(MaterialTheme.shapes.large)
            .background(Brush.horizontalGradient(colors))
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
            Icon(Icons.Outlined.ImageSearch, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimary)
            Text(
                stringResource(R.string.search),
                color = MaterialTheme.colorScheme.onPrimary,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
private fun CompactSearchBar(
    selectedCategory: Category?,
    state: SearchUiState,
    onEdit: () -> Unit,
    onCancel: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 8.dp),
        color = MaterialTheme.colorScheme.surfaceContainerHigh.copy(alpha = .96f),
        shape = MaterialTheme.shapes.large,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = .2f)),
        shadowElevation = 2.dp,
    ) {
        Row(
            Modifier.padding(start = 14.dp, end = 6.dp, top = 8.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(selectedCategory?.emoji ?: "🎨", style = MaterialTheme.typography.titleLarge)
            Column(Modifier.weight(1f)) {
                Text(
                    selectedCategory?.label ?: stringResource(R.string.search_results),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    if (state.loading) {
                        stringResource(
                            R.string.search_progress_details,
                            state.completedSources,
                            state.totalSources,
                            state.requestCount,
                            state.estimatedRequests,
                        )
                    } else {
                        stringResource(R.string.search_summary, state.posts.size, state.requestCount)
                    },
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            if (state.loading) {
                IconButton(onClick = onCancel) {
                    Icon(Icons.Outlined.Close, stringResource(R.string.cancel_search))
                }
            }
            IconButton(onClick = onEdit) {
                Icon(Icons.Outlined.Tune, stringResource(R.string.edit_search))
            }
        }
    }
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun SearchOptionsCard(
    expanded: Boolean,
    options: SearchOptions,
    blurNsfw: Boolean,
    estimatedRequests: Int,
    onExpandedChange: (Boolean) -> Unit,
    onBlurNsfwChange: (Boolean) -> Unit,
    onOptionsChange: (SearchOptions) -> Unit,
) {
    ArtFinderPanel(Modifier.fillMaxWidth(), contentPadding = PaddingValues(0.dp)) {
        Row(
            Modifier.fillMaxWidth().clickable { onExpandedChange(true) }.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.Tune, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(stringResource(R.string.search_options), fontWeight = FontWeight.Bold)
                Text(
                    stringResource(R.string.pages_and_requests, options.pages, estimatedRequests),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
    if (expanded) {
        ModalBottomSheet(onDismissRequest = { onExpandedChange(false) }) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .heightIn(max = 640.dp)
                    .verticalScroll(rememberScrollState())
                    .padding(start = 20.dp, end = 20.dp, bottom = 28.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text(stringResource(R.string.search_options), style = MaterialTheme.typography.titleLarge)
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
                        ArtFinderPill("SFW", options.includeSfw, { toggleRating(options, "sfw", onOptionsChange) })
                    }
                    item {
                        ArtFinderPill(
                            stringResource(R.string.sensitive),
                            options.includeSensitive,
                            { toggleRating(options, "sensitive", onOptionsChange) },
                        )
                    }
                    item {
                        ArtFinderPill("NSFW", options.includeNsfw, { toggleRating(options, "nsfw", onOptionsChange) })
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
                        ArtFinderPill(
                            selected = options.periodDays == days,
                            onClick = { onOptionsChange(options.copy(periodDays = days)) },
                            label = stringResource(label),
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
    ArtFinderPanel(Modifier.fillMaxWidth(), contentPadding = PaddingValues(6.dp)) {
        ArtworkPreview(
            model = post.previewModel(context),
            contentDescription = post.tags,
            badge = post.source.label,
            hidden = hiddenNsfw,
            onReveal = { nsfwRevealed = true },
            onOpen = onOpen,
            modifier = Modifier,
        )
        Column(Modifier.padding(start = 8.dp, end = 8.dp, top = 4.dp, bottom = 6.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        post.artist.ifBlank { stringResource(R.string.unknown_artist) },
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        fontWeight = FontWeight.Bold,
                    )
                    Text("★ ${post.score} · ${post.width}×${post.height}", style = MaterialTheme.typography.bodySmall)
                }
                if (post.pageUrl.isNotBlank()) {
                    IconButton(onClick = {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(post.pageUrl)))
                    }) { Icon(Icons.AutoMirrored.Outlined.OpenInNew, stringResource(R.string.open_source)) }
                }
            }
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ArtFinderSecondaryButton(
                    label = stringResource(R.string.keep),
                    icon = Icons.Outlined.BookmarkBorder,
                    onClick = onKeep,
                    enabled = uid !in state.saving,
                    modifier = Modifier.weight(1f),
                )
                ArtFinderSecondaryButton(
                    label = if (uid in state.saving) "…" else stringResource(R.string.download),
                    icon = Icons.Outlined.Download,
                    onClick = { viewModel.download(post) },
                    enabled = uid !in state.saving,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
