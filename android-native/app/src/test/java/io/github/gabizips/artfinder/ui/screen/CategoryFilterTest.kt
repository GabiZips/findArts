package io.github.gabizips.artfinder.ui.screen

import io.github.gabizips.artfinder.model.Category
import org.junit.Assert.assertEquals
import org.junit.Test

class CategoryFilterTest {
    private val categories = listOf(
        Category(
            key = "vex",
            label = "Vex",
            tags = "vex_(league_of_legends)",
            group = "League of Legends",
            emoji = "💚",
            sourceTags = mapOf("pixiv" to listOf("ヴェックス")),
        ),
        Category(
            key = "shadow",
            label = "Shadow",
            tags = "shadow_the_hedgehog",
            group = "Sonic",
            emoji = "🖤",
        ),
    )

    @Test
    fun searchesLabelsBaseTagsAndSourceOverrides() {
        assertEquals(listOf("vex"), filterCategories(categories, "vex", null).map(Category::key))
        assertEquals(listOf("vex"), filterCategories(categories, "league", null).map(Category::key))
        assertEquals(listOf("vex"), filterCategories(categories, "ヴェックス", null).map(Category::key))
    }

    @Test
    fun combinesGroupFilterAndStableSorting() {
        assertEquals(listOf("shadow"), filterCategories(categories, "", "Sonic").map(Category::key))
        assertEquals(listOf("vex", "shadow"), filterCategories(categories, "", null).map(Category::key))
    }
}
