package io.github.gabizips.artfinder

import android.app.Application
import io.github.gabizips.artfinder.data.GalleryRepository
import io.github.gabizips.artfinder.data.PairingRepository
import io.github.gabizips.artfinder.data.SearchRepository
import io.github.gabizips.artfinder.data.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class ArtFinderApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        val settings = SettingsRepository(this)
        container = AppContainer(
            settings = settings,
            pairing = PairingRepository(),
            search = SearchRepository(),
            gallery = GalleryRepository(this, settings),
        )
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
            settings.migrateLegacyPythonData()
        }
    }
}

data class AppContainer(
    val settings: SettingsRepository,
    val pairing: PairingRepository,
    val search: SearchRepository,
    val gallery: GalleryRepository,
)
