package io.github.gabizips.artfinder.data.source

import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import org.junit.Assert.assertEquals
import org.junit.Test

class SourceQueryTest {
    @Test
    fun explicitSourceOverrideAlwaysWins() {
        val category = Category(
            key = "vex_lol",
            label = "Vex",
            tags = "vex_(league_of_legends)",
            sourceTags = mapOf("pixiv" to listOf("custom-vex")),
        )
        assertEquals(listOf("custom-vex"), category.queriesFor(ArtSource.PIXIV))
    }

    @Test
    fun knownCharactersUsePixivMapping() {
        val vex = Category("vex_lol", "Vex", "vex_(league_of_legends)")
        val cyberpunkV = Category("v_cyberpunk", "V", "v_(cyberpunk_2077)")
        assertEquals(listOf("ヴェックス"), vex.queriesFor(ArtSource.PIXIV))
        assertEquals(listOf("サイバーパンク2077 V"), cyberpunkV.queriesFor(ArtSource.PIXIV))
    }

    @Test
    fun genericSourcesKeepConfiguredBooruTag() {
        val category = Category("vex_lol", "Vex", "vex_(league_of_legends)")
        assertEquals(listOf("vex_(league_of_legends)"), category.queriesFor(ArtSource.DANBOORU))
    }
}
