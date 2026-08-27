package io.github.gabizips.artfinder.ui.screen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Clear
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Tag
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.ui.component.CategoryEditorDialog
import io.github.gabizips.artfinder.ui.component.ArtFinderBackdrop
import io.github.gabizips.artfinder.ui.component.ArtFinderIconTile
import io.github.gabizips.artfinder.ui.component.ArtFinderPanel
import io.github.gabizips.artfinder.ui.component.ArtFinderPill
import io.github.gabizips.artfinder.ui.component.EmptyState
import io.github.gabizips.artfinder.ui.component.ScreenHeader

internal fun filterCategories(
    categories: List<Category>,
    query: String,
    selectedGroup: String?,
): List<Category> {
    val normalizedQuery = query.trim()
    return categories
        .asSequence()
        .filter { selectedGroup == null || it.group == selectedGroup }
        .filter { category ->
            normalizedQuery.isBlank() || listOf(
                category.label,
                category.group,
                category.tags,
                category.sourceTags.values.flatten().joinToString(" "),
            ).any { it.contains(normalizedQuery, ignoreCase = true) }
        }
        .sortedWith(compareBy(Category::group, Category::label))
        .toList()
}

@Composable
fun TagsScreen(categories: List<Category>, viewModel: MainViewModel) {
    var editing by remember { mutableStateOf<Category?>(null) }
    var deleting by remember { mutableStateOf<Category?>(null) }
    var creating by rememberSaveable { mutableStateOf(false) }
    var query by rememberSaveable { mutableStateOf("") }
    var selectedGroup by rememberSaveable { mutableStateOf<String?>(null) }

    val groups = remember(categories) { categories.map(Category::group).distinct().sorted() }
    val visibleCategories = remember(categories, query, selectedGroup) {
        filterCategories(categories, query, selectedGroup)
    }

    ArtFinderBackdrop {
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            ScreenHeader(
                title = stringResource(R.string.tags_characters),
                description = stringResource(R.string.source_specific_search),
                action = {
                    ArtFinderPill(
                        label = stringResource(R.string.new_tag),
                        selected = true,
                        onClick = { creating = true },
                        icon = Icons.Outlined.Add,
                    )
                },
            )
            OutlinedTextField(
                value = query,
                onValueChange = { query = it.take(200) },
                label = { Text(stringResource(R.string.search_tags)) },
                leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null) },
                trailingIcon = if (query.isNotBlank()) {
                    {
                        IconButton(onClick = { query = "" }) {
                            Icon(Icons.Outlined.Clear, stringResource(R.string.close))
                        }
                    }
                } else {
                    null
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    ArtFinderPill(
                        selected = selectedGroup == null,
                        onClick = { selectedGroup = null },
                        label = stringResource(R.string.all_groups),
                    )
                }
                items(groups, key = { it }) { group ->
                    ArtFinderPill(
                        selected = selectedGroup == group,
                        onClick = { selectedGroup = group },
                        label = group,
                    )
                }
            }
            Text(
                stringResource(R.string.tag_count, visibleCategories.size),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
        }

        if (visibleCategories.isEmpty()) {
            EmptyState(
                icon = Icons.Outlined.Tag,
                title = stringResource(R.string.no_tag_results_title),
                description = stringResource(R.string.no_tag_results_description),
                modifier = Modifier.fillMaxSize(),
                actionLabel = if (categories.isEmpty()) stringResource(R.string.new_tag) else null,
                onAction = if (categories.isEmpty()) ({ creating = true }) else null,
            )
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                visibleCategories.groupBy(Category::group).forEach { (group, values) ->
                    item("group:$group") {
                        Text(
                            group,
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(start = 4.dp, top = 8.dp),
                        )
                    }
                    items(values, key = Category::key) { category ->
                        ArtFinderPanel(Modifier.fillMaxWidth(), contentPadding = PaddingValues(12.dp)) {
                            Row(
                                Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                ArtFinderIconTile(emoji = category.emoji, compact = true)
                                Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                                    Text(category.label, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                    Text(
                                        category.tags,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                    if (category.sourceTags.isNotEmpty()) {
                                        Text(
                                            stringResource(R.string.overrides, category.sourceTags.keys.joinToString()),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.primary,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                        )
                                    }
                                }
                                IconButton(onClick = { editing = category }) {
                                    Icon(Icons.Outlined.Edit, stringResource(R.string.edit))
                                }
                                IconButton(onClick = { deleting = category }) {
                                    Icon(Icons.Outlined.Delete, stringResource(R.string.delete))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    }

    if (creating || editing != null) {
        CategoryEditorDialog(
            initial = editing,
            groups = (
                categories.map(Category::group) + listOf(
                    "Geral",
                    "Sonic",
                    "Hazbin Hotel",
                    "Helluva Boss",
                    "League of Legends",
                    "Jogos",
                    "Animes",
                )
                ).distinct(),
            onDismiss = { creating = false; editing = null },
            onSave = { viewModel.upsertCategory(it); creating = false; editing = null },
        )
    }

    deleting?.let { category ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            title = { Text(stringResource(R.string.delete_tag_title)) },
            text = { Text(stringResource(R.string.delete_tag_confirmation, category.label)) },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.deleteCategory(category.key)
                    deleting = null
                }) { Text(stringResource(R.string.delete)) }
            },
            dismissButton = {
                TextButton(onClick = { deleting = null }) { Text(stringResource(R.string.cancel)) }
            },
        )
    }
}
