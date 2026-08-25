package io.github.gabizips.artfinder.ui.screen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Key
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.SettingsSnapshot
import io.github.gabizips.artfinder.ui.component.ScreenHeader
import io.github.gabizips.artfinder.ui.component.SectionHeader
import io.github.gabizips.artfinder.ui.component.StatusBadge

@Composable
fun SettingsScreen(settings: SettingsSnapshot, viewModel: MainViewModel) {
    val busy by viewModel.pairingBusy.collectAsStateWithLifecycle()
    val message by viewModel.pairingMessage.collectAsStateWithLifecycle()
    val messageIsError by viewModel.pairingError.collectAsStateWithLifecycle()
    var code by remember { mutableStateOf("") }
    var replace by remember { mutableStateOf(false) }
    var editingCredential by remember { mutableStateOf<String?>(null) }

    LazyColumn(
        modifier = Modifier.fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            ScreenHeader(
                title = stringResource(R.string.settings),
                description = stringResource(R.string.settings_description),
            )
        }
        item {
            OutlinedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(stringResource(R.string.pair_devices), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(stringResource(R.string.pair_instructions))
                    OutlinedTextField(
                        value = code, onValueChange = { code = it.take(12_000) },
                        label = { Text(stringResource(R.string.paste_code)) }, minLines = 3,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = !replace, onClick = { replace = false }); Text(stringResource(R.string.merge_tags))
                        RadioButton(selected = replace, onClick = { replace = true }); Text(stringResource(R.string.replace_tags))
                    }
                    Button(
                        onClick = { viewModel.importPairing(code, replace) },
                        enabled = code.startsWith("artfinder-pair:v1:") && !busy,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        if (busy) CircularProgressIndicator(Modifier.height(20.dp)) else Text(stringResource(R.string.import_configuration))
                    }
                    message?.let {
                        Surface(
                            color = if (messageIsError) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.secondaryContainer,
                            contentColor = if (messageIsError) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onSecondaryContainer,
                            shape = MaterialTheme.shapes.small,
                        ) {
                            Text(it, modifier = Modifier.padding(10.dp), style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
        item {
            SectionHeader(
                title = stringResource(R.string.sources_credentials),
                supportingText = stringResource(R.string.configured_sources, settings.configuredCredentials.size),
            )
        }
        items(ArtSource.entries) { source ->
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(source.label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                        if (source.credentialKeys.isEmpty()) {
                            StatusBadge(stringResource(R.string.no_credentials_needed), positive = true)
                        }
                    }
                    source.credentialKeys.forEach { key ->
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(key, style = MaterialTheme.typography.bodySmall)
                                StatusBadge(
                                    label = if (key in settings.configuredCredentials) {
                                        stringResource(R.string.configured)
                                    } else {
                                        stringResource(R.string.not_configured)
                                    },
                                    positive = key in settings.configuredCredentials,
                                    modifier = Modifier.padding(top = 4.dp),
                                )
                            }
                            TextButton(onClick = { editingCredential = key }) { Icon(Icons.Outlined.Key, null); Text(" ${stringResource(R.string.change)}") }
                        }
                    }
                }
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(stringResource(R.string.local_data_only), style = MaterialTheme.typography.labelLarge)
                Text(stringResource(R.string.legal_notice), style = MaterialTheme.typography.bodySmall)
            }
        }
    }

    editingCredential?.let { key ->
        CredentialDialog(key, key in settings.configuredCredentials, onDismiss = { editingCredential = null }) { value ->
            viewModel.saveCredential(key, value); editingCredential = null
        }
    }
}

@Composable
private fun CredentialDialog(key: String, configured: Boolean, onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var value by remember(key) { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(key) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (configured) Text(stringResource(R.string.protected_value))
                OutlinedTextField(
                    value = value, onValueChange = { value = it.take(4096) },
                    label = { Text(stringResource(R.string.new_value)) }, visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = { TextButton(onClick = { onSave(value) }) { Text(if (value.isBlank()) stringResource(R.string.remove) else stringResource(R.string.save)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
