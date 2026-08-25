package io.github.gabizips.artfinder

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.Crossfade
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Collections
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Tag
import androidx.compose.material.icons.outlined.Collections
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Tag
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import io.github.gabizips.artfinder.ui.screen.GalleryScreen
import io.github.gabizips.artfinder.ui.screen.SearchScreen
import io.github.gabizips.artfinder.ui.screen.SettingsScreen
import io.github.gabizips.artfinder.ui.screen.TagsScreen
import io.github.gabizips.artfinder.ui.theme.ArtFinderTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { ArtFinderTheme { ArtFinderApp() } }
    }
}

private data class Destination(val label: String, val icon: ImageVector, val selectedIcon: ImageVector)

@Composable
private fun ArtFinderApp(viewModel: MainViewModel = viewModel()) {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val search by viewModel.searchState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(search.message) {
        search.message?.let { message ->
            snackbarHostState.showSnackbar(message)
            viewModel.clearMessages()
        }
    }
    val destinations = listOf(
        Destination(stringResource(R.string.search), Icons.Outlined.Search, Icons.Filled.Search),
        Destination(stringResource(R.string.tags), Icons.Outlined.Tag, Icons.Filled.Tag),
        Destination(stringResource(R.string.gallery), Icons.Outlined.Collections, Icons.Filled.Collections),
        Destination(stringResource(R.string.settings), Icons.Outlined.Settings, Icons.Filled.Settings),
    )
    Scaffold(
        contentWindowInsets = WindowInsets.safeDrawing,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surfaceContainer,
                tonalElevation = 4.dp,
            ) {
                destinations.forEachIndexed { index, destination ->
                    NavigationBarItem(
                        selected = selected == index, onClick = { selected = index },
                        icon = {
                            Icon(
                                if (selected == index) destination.selectedIcon else destination.icon,
                                contentDescription = destination.label,
                            )
                        },
                        label = { Text(destination.label) },
                        colors = NavigationBarItemDefaults.colors(
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                        ),
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            Crossfade(targetState = selected, label = "main navigation") { destination ->
                when (destination) {
                    0 -> SearchScreen(settings, search, viewModel, onManageTags = { selected = 1 })
                    1 -> TagsScreen(settings.categories, viewModel)
                    2 -> GalleryScreen(
                        settings.gallery, settings.collections, settings.displayPreferences.blurNsfw,
                        search.saving, viewModel,
                    )
                    else -> SettingsScreen(settings, viewModel)
                }
            }
        }
    }
}
