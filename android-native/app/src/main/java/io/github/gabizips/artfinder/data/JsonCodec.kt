package io.github.gabizips.artfinder.data

import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.ArtCollection
import io.github.gabizips.artfinder.model.GalleryItem
import org.json.JSONArray
import org.json.JSONObject

internal object JsonCodec {
    fun categoriesToJson(categories: List<Category>): String {
        val root = JSONObject()
        categories.forEach { category ->
            root.put(category.key, JSONObject().apply {
                put("label", category.label)
                put("tags", category.tags)
                put("group", category.group)
                put("emoji", category.emoji)
                put("color", category.color)
                put("favorite", category.favorite)
                put("source_tags", JSONObject().apply {
                    category.sourceTags.forEach { (source, queries) ->
                        put(source, JSONArray(queries))
                    }
                })
            })
        }
        return root.toString()
    }

    fun categoriesFromJson(raw: String): List<Category> {
        if (raw.isBlank()) return emptyList()
        val root = JSONObject(raw)
        return root.keys().asSequence().mapNotNull { key ->
            val value = root.optJSONObject(key) ?: return@mapNotNull null
            val tags = value.optString("tags").trim()
            if (key.isBlank() || tags.isBlank()) return@mapNotNull null
            val sourceTags = mutableMapOf<String, List<String>>()
            value.optJSONObject("source_tags")?.let { sourceObject ->
                sourceObject.keys().forEach { source ->
                    val queries = sourceObject.optJSONArray(source)?.let { array ->
                        (0 until array.length()).mapNotNull { array.optString(it).trim().takeIf(String::isNotEmpty) }
                    } ?: listOfNotNull(sourceObject.optString(source).trim().takeIf(String::isNotEmpty))
                    if (queries.isNotEmpty()) sourceTags[normalizeSource(source)] = queries.distinct()
                }
            }
            Category(
                key = key,
                label = value.optString("label", key.replace('_', ' ')).ifBlank { key },
                tags = tags,
                group = value.optString("group", "Geral").ifBlank { "Geral" },
                emoji = value.optString("emoji", "🎨").ifBlank { "🎨" },
                color = value.optString("color", "#6366F1").takeIf { it.matches(Regex("#[0-9a-fA-F]{6}")) } ?: "#6366F1",
                favorite = value.optBoolean("favorite", false),
                sourceTags = sourceTags,
            )
        }.toList()
    }

    fun galleryToJson(items: List<GalleryItem>): String = JSONArray().apply {
        items.forEach { item -> put(JSONObject().apply {
            put("uid", item.uid)
            put("content_uri", item.contentUri)
            put("source", item.source)
            put("source_id", item.sourceId)
            put("page_url", item.pageUrl)
            put("preview_url", item.previewUrl)
            put("original_url", item.originalUrl)
            put("artist", item.artist)
            put("category_key", item.categoryKey)
            put("saved_at", item.savedAt)
            put("rating", item.rating)
            put("collection_ids", JSONArray(item.collectionIds.toList()))
        }) }
    }.toString()

    fun galleryFromJson(raw: String): List<GalleryItem> {
        if (raw.isBlank()) return emptyList()
        val array = JSONArray(raw)
        return (0 until array.length()).mapNotNull { index ->
            val value = array.optJSONObject(index) ?: return@mapNotNull null
            val uri = value.optString("content_uri")
            val originalUrl = value.optString("original_url")
            val previewUrl = value.optString("preview_url")
            val uid = value.optString("uid")
            if (uid.isBlank() || (uri.isBlank() && originalUrl.isBlank() && previewUrl.isBlank())) return@mapNotNull null
            val collectionIds = value.optJSONArray("collection_ids")?.let { ids ->
                (0 until ids.length()).mapNotNull { ids.optString(it).takeIf(String::isNotBlank) }.toSet()
            }.orEmpty()
            GalleryItem(
                uid = uid, contentUri = uri,
                source = value.optString("source"), sourceId = value.optString("source_id"),
                pageUrl = value.optString("page_url"), previewUrl = previewUrl, originalUrl = originalUrl,
                artist = value.optString("artist"),
                categoryKey = value.optString("category_key"), savedAt = value.optLong("saved_at"),
                rating = value.optString("rating", "sfw"), collectionIds = collectionIds,
            )
        }
    }

    fun collectionsToJson(collections: List<ArtCollection>): String = JSONArray().apply {
        collections.forEach { collection -> put(JSONObject().apply {
            put("id", collection.id)
            put("name", collection.name)
            put("created_at", collection.createdAt)
        }) }
    }.toString()

    fun collectionsFromJson(raw: String): List<ArtCollection> {
        if (raw.isBlank()) return emptyList()
        val array = JSONArray(raw)
        return (0 until array.length()).mapNotNull { index ->
            val value = array.optJSONObject(index) ?: return@mapNotNull null
            val id = value.optString("id")
            val name = value.optString("name").trim()
            if (id.isBlank() || name.isBlank()) return@mapNotNull null
            ArtCollection(id, name, value.optLong("created_at"))
        }.distinctBy(ArtCollection::id)
    }

    fun stringMapToJson(values: Map<String, String>): String = JSONObject(values).toString()

    fun stringMapFromJson(raw: String): Map<String, String> {
        if (raw.isBlank()) return emptyMap()
        val value = JSONObject(raw)
        return value.keys().asSequence().associateWith { value.optString(it) }
    }

    private fun normalizeSource(source: String) = if (source.lowercase() == "bsky") "bluesky" else source.lowercase()
}
