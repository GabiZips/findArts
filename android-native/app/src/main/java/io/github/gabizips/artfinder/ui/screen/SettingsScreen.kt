package io.github.gabizips.artfinder.ui.screen

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Key
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.gabizips.artfinder.MainViewModel
import io.github.gabizips.artfinder.R
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.SettingsSnapshot

@Composable
fun SettingsScreen(settings: SettingsSnapshot, viewModel: MainViewModel) {
    val context = LocalContext.current
    val busy by viewModel.pairingBusy.collectAsStateWithLifecycle()
    val message by viewModel.pairingMessage.collectAsStateWithLifecycle()
    val messageIsError by viewModel.pairingError.collectAsStateWithLifecycle()
    var code by remember { mutableStateOf("") }
    var replace by remember { mutableStateOf(false) }
    var showScanner by remember { mutableStateOf(false) }
    var editingCredential by remember { mutableStateOf<String?>(null) }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        showScanner = granted
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(stringResource(R.string.settings), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(stringResource(R.string.local_data_only))
        }
        item {
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(stringResource(R.string.pair_devices), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(stringResource(R.string.pair_instructions))
                    Button(onClick = {
                        if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) showScanner = true
                        else permission.launch(Manifest.permission.CAMERA)
                    }, modifier = Modifier.fillMaxWidth()) {
                        Icon(Icons.Outlined.QrCodeScanner, null); Text(" ${stringResource(R.string.scan_qr)}")
                    }
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
                    message?.let { Text(it, color = if (messageIsError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.secondary) }
                }
            }
        }
        item { Text(stringResource(R.string.sources_credentials), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold) }
        items(ArtSource.entries) { source ->
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text(source.label, fontWeight = FontWeight.Bold)
                    if (source.credentialKeys.isEmpty()) Text(stringResource(R.string.no_credentials_needed), style = MaterialTheme.typography.bodySmall)
                    source.credentialKeys.forEach { key ->
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(key, style = MaterialTheme.typography.bodySmall)
                                Text(if (key in settings.configuredCredentials) stringResource(R.string.configured) else stringResource(R.string.not_configured))
                            }
                            TextButton(onClick = { editingCredential = key }) { Icon(Icons.Outlined.Key, null); Text(" ${stringResource(R.string.change)}") }
                        }
                    }
                }
            }
        }
        item {
            Text(
                stringResource(R.string.legal_notice),
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }

    if (showScanner) {
        Dialog(onDismissRequest = { showScanner = false }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
            Box(Modifier.fillMaxSize()) {
                QrScanner(onCode = { value -> code = value; showScanner = false })
                TextButton(
                    onClick = { showScanner = false },
                    modifier = Modifier.align(Alignment.TopEnd).safeDrawingPadding().padding(12.dp),
                ) { Text(stringResource(R.string.close)) }
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
