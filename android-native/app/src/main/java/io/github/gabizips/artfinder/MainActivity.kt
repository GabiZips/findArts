package io.github.gabizips.artfinder

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.Crossfade
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
            ArtFinderNavigationBar(destinations, selected) { selected = it }
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

@Composable
private fun ArtFinderNavigationBar(
    destinations: List<Destination>,
    selected: Int,
    onSelected: (Int) -> Unit,
) {
    Surface(color = MaterialTheme.colorScheme.surfaceContainerHigh, shadowElevation = 12.dp) {
        Column {
            HorizontalDivider(color = MaterialTheme.colorScheme.primary.copy(alpha = .22f))
            Row(
                Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 6.dp, vertical = 7.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
            ) {
                destinations.forEachIndexed { index, destination ->
                    val active = selected == index
                    Column(
                        Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(18.dp))
                            .clickable { onSelected(index) }
                            .padding(vertical = 3.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(2.dp),
                    ) {
                        Box(
                            Modifier
                                .width(58.dp)
                                .height(36.dp)
                                .clip(RoundedCornerShape(18.dp))
                                .background(
                                    if (active) {
                                        Brush.horizontalGradient(
                                            listOf(
                                                MaterialTheme.colorScheme.primary.copy(alpha = .9f),
                                                MaterialTheme.colorScheme.tertiary.copy(alpha = .78f),
                                            ),
                                        )
                                    } else {
                                        Brush.horizontalGradient(listOf(androidx.compose.ui.graphics.Color.Transparent, androidx.compose.ui.graphics.Color.Transparent))
                                    },
                                ),
                            contentAlignment = Alignment.Center,
                        ) {
                            Icon(
                                if (active) destination.selectedIcon else destination.icon,
                                contentDescription = destination.label,
                                tint = if (active) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Text(
                            destination.label,
                            color = if (active) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurfaceVariant,
                            fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                            fontSize = 11.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
        }
    }
}
