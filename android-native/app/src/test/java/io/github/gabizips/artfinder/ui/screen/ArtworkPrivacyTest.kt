package io.github.gabizips.artfinder.ui.screen

import io.github.gabizips.artfinder.ui.component.shouldHideArtwork
import org.junit.Assert.*
import org.junit.Test

class ArtworkPrivacyTest {
    @Test fun sensitiveRatingsHiddenUntilRevealOnEveryApiLevel() {
        for (rating in listOf("nsfw", "explicit", "e", "sensitive", "questionable", "q", "s", " NSFW ")) {
            assertTrue(shouldHideArtwork(rating, true))
            assertFalse(shouldHideArtwork(rating, true, revealed = true))
            assertFalse(shouldHideArtwork(rating, false))
        }
        assertFalse(shouldHideArtwork("sfw", true))
    }
}
