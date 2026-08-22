package io.github.gabizips.artfinder.data

import io.github.gabizips.artfinder.data.source.epochSeconds
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOptions
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchOptionsTest {
    private fun post(
        id: String,
        rating: String = "sfw",
        score: Int = 10,
        date: Long = 1_700_000_000,
        tags: String = "art",
        isAi: Boolean = false,
        width: Int = 100,
        height: Int = 100,
    ) = ArtPost(
        id = id, source = ArtSource.DANBOORU, url = "https://example.com/$id.jpg",
        width = width, height = height, score = score, tags = tags, rating = rating,
        categoryKey = "test", postDate = date, isAi = isAi,
    )

    @Test
    fun filtersRatingScoreAgeAndAiWithoutFilteringResolution() {
        val now = 1_700_000_000L
        val posts = listOf(
            post("small", width = 50, height = 50),
            post("nsfw", rating = "nsfw"),
            post("old", date = now - 40 * 86_400L),
            post("unknown-date", date = 0),
            post("low-score", score = 1),
            post("ai", tags = "ai_generated"),
        )
        val options = SearchOptions(
            includeSfw = true, includeSensitive = false, includeNsfw = false,
            periodDays = 30, minScore = 5, hideAi = true,
        )

        assertEquals(listOf("small"), applySearchOptions(posts, options, now).map(ArtPost::id))
    }

    @Test
    fun nsfwCanBeExplicitlyIncluded() {
        val options = SearchOptions(includeSfw = false, includeSensitive = false, includeNsfw = true)
        assertEquals(listOf("nsfw"), applySearchOptions(listOf(post("safe"), post("nsfw", "nsfw")), options).map(ArtPost::id))
    }

    @Test
    fun requestEstimateIncludesPagesQueriesAndAuthentication() {
        val category = Category(
            key = "test", label = "Test", tags = "test",
            sourceTags = mapOf("pixiv" to listOf("one", "two")),
        )
        val sources = setOf(ArtSource.DANBOORU, ArtSource.PIXIV, ArtSource.BLUESKY)

        assertEquals(22, SearchRepository().estimateRequestCount(category, sources, 5))
    }

    @Test
    fun parsesNumericMillisecondsAndIsoDates() {
        assertEquals(1_700_000_000L, JSONObject().put("date", 1_700_000_000_000L).epochSeconds("date"))
        assertEquals(1_700_000_000L, JSONObject().put("date", "2023-11-14T22:13:20Z").epochSeconds("date"))
        assertEquals(1_700_000_000L, JSONObject().put("date", "Tue Nov 14 22:13:20 +0000 2023").epochSeconds("date"))
        assertTrue(JSONObject().epochSeconds("missing") == 0L)
    }
}
