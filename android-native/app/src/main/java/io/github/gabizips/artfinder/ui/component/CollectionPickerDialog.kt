package io.github.gabizips.artfinder.ui.component

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.model.ArtCollection

@Composable
fun CollectionPickerDialog(
    collections: List<ArtCollection>,
    initialSelection: Set<String>,
    onDismiss: () -> Unit,
    onConfirm: (Set<String>) -> Unit,
) {
    var selected by remember(initialSelection) { mutableStateOf(initialSelection) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.choose_collections)) },
        text = {
            Column {
                if (collections.isEmpty()) Text(stringResource(R.string.no_collections_hint))
                collections.forEach { collection ->
                    Row(
                        Modifier.fillMaxWidth().clickable {
                            selected = if (collection.id in selected) selected - collection.id else selected + collection.id
                        }.padding(vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Checkbox(
                            checked = collection.id in selected,
                            onCheckedChange = { checked ->
                                selected = if (checked) selected + collection.id else selected - collection.id
                            },
                        )
                        Text(collection.name)
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(selected) }) { Text(stringResource(R.string.confirm)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
