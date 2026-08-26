package io.github.gabizips.artfinder.ui.screen

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Folder
import androidx.compose.material.icons.outlined.FolderOff
import androidx.compose.material.icons.outlined.PhotoLibrary
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.model.ArtCollection
import io.github.gabizips.artfinder.model.GalleryItem
import io.github.gabizips.artfinder.ui.component.ArtworkPreview
import io.github.gabizips.artfinder.ui.component.CollectionPickerDialog
import io.github.gabizips.artfinder.ui.component.EmptyState
import io.github.gabizips.artfinder.ui.component.ScreenHeader
import io.github.gabizips.artfinder.ui.component.StatusBadge
import io.github.gabizips.artfinder.ui.component.ViewerImage
import io.github.gabizips.artfinder.ui.component.ZoomableImageViewer
import io.github.gabizips.artfinder.ui.imageModel
import io.github.gabizips.artfinder.ui.originalModel

@Composable
fun GalleryScreen(
    items: List<GalleryItem>,
    collections: List<ArtCollection>,
    blurNsfw: Boolean,
    busyItems: Set<String>,
    viewModel: MainViewModel,
) {
    val context = LocalContext.current
    var selectedCollectionId by rememberSaveable { mutableStateOf<String?>(null) }
    var viewerUid by rememberSaveable { mutableStateOf<String?>(null) }
    var pickerUid by rememberSaveable { mutableStateOf<String?>(null) }
    var deletingUid by rememberSaveable { mutableStateOf<String?>(null) }
    var creatingCollection by rememberSaveable { mutableStateOf(false) }
    var renamingCollection by rememberSaveable { mutableStateOf(false) }
    var deletingCollection by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(collections, selectedCollectionId) {
        if (selectedCollectionId != null && collections.none { it.id == selectedCollectionId }) selectedCollectionId = null
    }
    val selectedCollection = collections.firstOrNull { it.id == selectedCollectionId }
    val visibleItems = remember(items, selectedCollectionId) {
        selectedCollectionId?.let { id -> items.filter { id in it.collectionIds } } ?: items
    }

    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            ScreenHeader(
                title = stringResource(R.string.gallery),
                description = stringResource(R.string.gallery_path),
                action = {
                    IconButton(onClick = { creatingCollection = true }) {
                        Icon(Icons.Outlined.Add, stringResource(R.string.new_collection))
                    }
                },
            )
            Text(
                stringResource(R.string.gallery_count, visibleItems.size),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    FilterChip(
                        selected = selectedCollectionId == null,
                        onClick = { selectedCollectionId = null },
                        label = { Text(stringResource(R.string.all_artworks)) },
                    )
                }
                items(collections, key = ArtCollection::id) { collection ->
                    FilterChip(
                        selected = selectedCollectionId == collection.id,
                        onClick = { selectedCollectionId = collection.id },
                        label = { Text(collection.name) },
                    )
                }
            }
            selectedCollection?.let { collection ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = { renamingCollection = true }) {
                        Icon(Icons.Outlined.Edit, null)
                        Text(stringResource(R.string.rename_collection))
                    }
                    TextButton(onClick = {
                        deletingCollection = true
                    }) {
                        Icon(Icons.Outlined.Delete, null)
                        Text(stringResource(R.string.delete_collection))
                    }
                }
            }
        }

        if (visibleItems.isEmpty()) {
            EmptyState(
                icon = if (selectedCollection == null) Icons.Outlined.PhotoLibrary else Icons.Outlined.FolderOff,
                title = stringResource(
                    if (selectedCollection == null) R.string.empty_gallery_title else R.string.empty_collection_title,
                ),
                description = stringResource(
                    if (selectedCollection == null) R.string.empty_gallery_description else R.string.no_saved_images,
                ),
                modifier = Modifier.fillMaxSize(),
            )
        } else {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(220.dp),
                modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                gridItems(visibleItems, key = GalleryItem::uid) { item ->
                    GalleryCard(
                        item = item,
                        blurNsfw = blurNsfw,
                        onOpen = { viewerUid = item.uid },
                        onCollections = { pickerUid = item.uid },
                        onDownload = { viewModel.download(item) },
                        onDelete = { deletingUid = item.uid },
                        busy = item.uid in busyItems,
                    )
                }
            }
        }
    }

    viewerUid?.let { uid ->
        val viewerImages = visibleItems.map { item ->
            ViewerImage(
                key = item.uid,
                model = item.originalModel(context),
                contentDescription = item.artist,
                title = item.artist.ifBlank { item.source.replaceFirstChar(Char::uppercase) },
                subtitle = item.source.replaceFirstChar(Char::uppercase),
                initiallyBlurred = blurNsfw && item.rating.equals("nsfw", ignoreCase = true),
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
    items.firstOrNull { it.uid == pickerUid }?.let { item ->
        CollectionPickerDialog(
            collections = collections,
            initialSelection = item.collectionIds,
            onDismiss = { pickerUid = null },
            onConfirm = { selected ->
                viewModel.setCollections(item, selected)
                pickerUid = null
            },
        )
    }
    if (creatingCollection) {
        CollectionNameDialog(
            title = stringResource(R.string.new_collection),
            initialValue = "",
            onDismiss = { creatingCollection = false },
            onConfirm = { name -> viewModel.createCollection(name); creatingCollection = false },
        )
    }
    if (renamingCollection && selectedCollection != null) {
        CollectionNameDialog(
            title = stringResource(R.string.rename_collection),
            initialValue = selectedCollection.name,
            onDismiss = { renamingCollection = false },
            onConfirm = { name -> viewModel.renameCollection(selectedCollection.id, name); renamingCollection = false },
        )
    }
    if (deletingCollection && selectedCollection != null) {
        AlertDialog(
            onDismissRequest = { deletingCollection = false },
            title = { Text(stringResource(R.string.delete_collection_title)) },
            text = { Text(stringResource(R.string.delete_collection_confirmation, selectedCollection.name)) },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.deleteCollection(selectedCollection.id)
                    selectedCollectionId = null
                    deletingCollection = false
                }) { Text(stringResource(R.string.delete)) }
            },
            dismissButton = {
                TextButton(onClick = { deletingCollection = false }) { Text(stringResource(R.string.cancel)) }
            },
        )
    }
    items.firstOrNull { it.uid == deletingUid }?.let { item ->
        AlertDialog(
            onDismissRequest = { deletingUid = null },
            title = { Text(stringResource(R.string.delete_art_title)) },
            text = { Text(stringResource(R.string.delete_art_confirmation)) },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.delete(item)
                    deletingUid = null
                }) { Text(stringResource(R.string.delete)) }
            },
            dismissButton = {
                TextButton(onClick = { deletingUid = null }) { Text(stringResource(R.string.cancel)) }
            },
        )
    }
}

@Composable
private fun GalleryCard(
    item: GalleryItem,
    blurNsfw: Boolean,
    onOpen: () -> Unit,
    onCollections: () -> Unit,
    onDownload: () -> Unit,
    onDelete: () -> Unit,
    busy: Boolean,
) {
    val context = LocalContext.current
    var nsfwRevealed by rememberSaveable(item.uid) { mutableStateOf(false) }
    val hiddenNsfw = blurNsfw && item.rating.equals("nsfw", ignoreCase = true) && !nsfwRevealed
    ElevatedCard(Modifier.fillMaxWidth()) {
        ArtworkPreview(
            model = item.imageModel(context),
            contentDescription = item.artist,
            badge = item.source.replaceFirstChar(Char::uppercase),
            hidden = hiddenNsfw,
            onReveal = { nsfwRevealed = true },
            onOpen = onOpen,
            modifier = Modifier.padding(6.dp),
        )
        Column(Modifier.padding(start = 12.dp, end = 12.dp, top = 6.dp, bottom = 10.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text(
                    item.artist.ifBlank { item.source },
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    fontWeight = FontWeight.Bold,
                )
                StatusBadge(
                    label = stringResource(if (item.contentUri.isBlank()) R.string.remote_only else R.string.downloaded),
                    positive = item.contentUri.isNotBlank(),
                )
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                if (item.pageUrl.isNotBlank()) IconButton(onClick = {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(item.pageUrl)))
                }) { Icon(Icons.AutoMirrored.Outlined.OpenInNew, stringResource(R.string.open_source)) }
                IconButton(onClick = onCollections) { Icon(Icons.Outlined.Folder, stringResource(R.string.choose_collections)) }
                if (item.contentUri.isBlank()) {
                    IconButton(onClick = onDownload, enabled = !busy) { Icon(Icons.Outlined.Download, stringResource(R.string.download)) }
                }
                IconButton(onClick = onDelete) { Icon(Icons.Outlined.Delete, stringResource(R.string.delete)) }
            }
        }
    }
}

@Composable
private fun CollectionNameDialog(
    title: String,
    initialValue: String,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var name by remember(initialValue) { mutableStateOf(initialValue) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it.take(80) },
                label = { Text(stringResource(R.string.collection_name)) },
                singleLine = true,
            )
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(name.trim()) }, enabled = name.isNotBlank()) {
                Text(stringResource(R.string.save))
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
