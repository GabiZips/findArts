package io.github.gabizips.artfinder.data

import io.github.gabizips.artfinder.model.Category
import org.junit.Assert.assertEquals
import org.junit.Test

class JsonCodecTest {
    @Test
    fun categoryRoundTripPreservesSourceOverrides() {
        val original = Category(
            key = "vex_lol", label = "Vex", tags = "vex_(league_of_legends)",
            group = "League of Legends", emoji = "💜",
            sourceTags = mapOf("pixiv" to listOf("ヴェックス"), "bluesky" to listOf("vex league of legends")),
        )
        assertEquals(listOf(original), JsonCodec.categoriesFromJson(JsonCodec.categoriesToJson(listOf(original))))
    }

    @Test
    fun invalidEmptyCategoriesAreIgnored() {
        assertEquals(emptyList<Category>(), JsonCodec.categoriesFromJson("{\"bad\":{\"tags\":\"\"}}"))
    }
}
