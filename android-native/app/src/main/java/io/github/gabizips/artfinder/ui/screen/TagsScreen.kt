package io.github.gabizips.artfinder.ui.screen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import java.text.Normalizer
import androidx.compose.ui.res.stringResource

@Composable
fun TagsScreen(categories: List<Category>, viewModel: MainViewModel) {
    var editing by remember { mutableStateOf<Category?>(null) }
    var creating by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Column {
                Text(stringResource(R.string.tags_characters), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(stringResource(R.string.source_specific_search), style = MaterialTheme.typography.bodyMedium)
            }
            Button(onClick = { creating = true }) { Icon(Icons.Outlined.Add, null); Text(" ${stringResource(R.string.new_tag)}") }
        }
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            categories.groupBy(Category::group).forEach { (group, values) ->
                item("group:$group") { Text(group, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp)) }
                items(values, key = Category::key) { category ->
                    ElevatedCard(Modifier.fillMaxWidth()) {
                        Row(Modifier.padding(12.dp)) {
                            Text(category.emoji, style = MaterialTheme.typography.headlineSmall)
                            Column(Modifier.weight(1f).padding(horizontal = 10.dp)) {
                                Text(category.label, fontWeight = FontWeight.Bold)
                                Text(category.tags, maxLines = 2, overflow = TextOverflow.Ellipsis)
                                if (category.sourceTags.isNotEmpty()) Text(
                                    stringResource(R.string.overrides, category.sourceTags.keys.joinToString()),
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                            IconButton(onClick = { editing = category }) { Icon(Icons.Outlined.Edit, stringResource(R.string.edit)) }
                            IconButton(onClick = { viewModel.deleteCategory(category.key) }) { Icon(Icons.Outlined.Delete, stringResource(R.string.delete)) }
                        }
                    }
                }
            }
        }
    }
    if (creating || editing != null) {
        CategoryDialog(
            initial = editing,
            groups = (categories.map(Category::group) + listOf("Geral", "Sonic", "Hazbin Hotel", "Helluva Boss", "League of Legends", "Jogos", "Animes")).distinct(),
            onDismiss = { creating = false; editing = null },
            onSave = { viewModel.upsertCategory(it); creating = false; editing = null },
        )
    }
}

@Composable
private fun CategoryDialog(initial: Category?, groups: List<String>, onDismiss: () -> Unit, onSave: (Category) -> Unit) {
    var label by remember(initial) { mutableStateOf(initial?.label.orEmpty()) }
    var tags by remember(initial) { mutableStateOf(initial?.tags.orEmpty()) }
    var group by remember(initial) { mutableStateOf(initial?.group ?: "Geral") }
    var emoji by remember(initial) { mutableStateOf(initial?.emoji ?: "🎨") }
    var groupExpanded by remember { mutableStateOf(false) }
    var overrides by remember(initial) {
        mutableStateOf(ArtSource.entries.associate { source -> source.id to initial?.sourceTags?.get(source.id).orEmpty().joinToString("; ") })
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (initial == null) stringResource(R.string.add_tag) else stringResource(R.string.edit_tag)) },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item { OutlinedTextField(label, { label = it }, label = { Text(stringResource(R.string.name)) }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(emoji, { emoji = it.take(8) }, label = { Text(stringResource(R.string.emoji)) }, modifier = Modifier.fillMaxWidth()) }
                item { OutlinedTextField(
                    tags, { tags = it }, label = { Text(stringResource(R.string.booru_tags)) },
                    supportingText = { Text(stringResource(R.string.booru_example)) }, modifier = Modifier.fillMaxWidth(),
                ) }
                item {
                    Column {
                        OutlinedTextField(group, { group = it }, label = { Text(stringResource(R.string.group)) }, modifier = Modifier.fillMaxWidth())
                        OutlinedButton(onClick = { groupExpanded = true }, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.choose_group)) }
                        DropdownMenu(expanded = groupExpanded, onDismissRequest = { groupExpanded = false }) {
                            groups.forEach { choice -> DropdownMenuItem(text = { Text(choice) }, onClick = { group = choice; groupExpanded = false }) }
                        }
                    }
                }
                item { Text(stringResource(R.string.source_tags), fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp)) }
                items(ArtSource.entries) { source ->
                    OutlinedTextField(
                        value = overrides[source.id].orEmpty(),
                        onValueChange = { overrides = overrides + (source.id to it) },
                        label = { Text(source.label) },
                        supportingText = { Text(stringResource(R.string.separate_semicolon)) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                enabled = label.isNotBlank() && tags.isNotBlank(),
                onClick = {
                    val key = initial?.key ?: normalizeKey(label)
                    val sourceTags = overrides.mapValues { (_, value) -> value.split(';', '\n').map(String::trim).filter(String::isNotBlank).distinct() }
                        .filterValues(List<String>::isNotEmpty)
                    onSave(Category(key, label.trim(), tags.trim(), group.trim().ifBlank { "Geral" }, emoji.trim().ifBlank { "🎨" }, sourceTags = sourceTags))
                },
            ) { Text(stringResource(R.string.save)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

private fun normalizeKey(value: String): String = Normalizer.normalize(value.lowercase(), Normalizer.Form.NFD)
    .replace(Regex("\\p{M}+"), "")
    .replace(Regex("[^a-z0-9]+"), "_")
    .trim('_').take(200)
