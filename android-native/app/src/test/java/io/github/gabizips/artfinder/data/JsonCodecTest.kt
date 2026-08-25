package io.github.gabizips.artfinder.data

import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.ArtCollection
import io.github.gabizips.artfinder.model.GalleryItem
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

    @Test
    fun galleryRoundTripPreservesNsfwRating() {
        val original = GalleryItem(
            uid = "pixiv:1", contentUri = "content://image/1", source = "pixiv", sourceId = "1",
            pageUrl = "https://example.com/1", previewUrl = "https://example.com/preview.jpg",
            originalUrl = "https://example.com/original.jpg", artist = "artist", categoryKey = "test",
            savedAt = 123L, rating = "nsfw", collectionIds = setOf("favorites", "refs"),
        )
        assertEquals(listOf(original), JsonCodec.galleryFromJson(JsonCodec.galleryToJson(listOf(original))))
    }

    @Test
    fun remoteOnlyGalleryItemAndCollectionsRoundTrip() {
        val item = GalleryItem(
            uid = "danbooru:2", source = "danbooru", sourceId = "2", pageUrl = "https://example.com/2",
            previewUrl = "https://example.com/p.jpg", originalUrl = "https://example.com/o.jpg",
            artist = "artist", categoryKey = "test", savedAt = 456L,
        )
        val collection = ArtCollection("refs", "Referências", 123L)

        assertEquals(listOf(item), JsonCodec.galleryFromJson(JsonCodec.galleryToJson(listOf(item))))
        assertEquals(listOf(collection), JsonCodec.collectionsFromJson(JsonCodec.collectionsToJson(listOf(collection))))
    }
}
