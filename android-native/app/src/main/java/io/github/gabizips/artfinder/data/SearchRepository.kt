package io.github.gabizips.artfinder.data

import io.github.gabizips.artfinder.data.source.BlueskySource
import io.github.gabizips.artfinder.data.source.DanbooruSource
import io.github.gabizips.artfinder.data.source.DeviantArtSource
import io.github.gabizips.artfinder.data.source.E621Source
import io.github.gabizips.artfinder.data.source.GelbooruSource
import io.github.gabizips.artfinder.data.source.PixivSource
import io.github.gabizips.artfinder.data.source.SafebooruSource
import io.github.gabizips.artfinder.data.source.SourceClient
import io.github.gabizips.artfinder.data.source.TumblrSource
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOutcome
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.supervisorScope

class SearchRepository {
    private val clients: Map<ArtSource, SourceClient> = listOf(
        DanbooruSource(), GelbooruSource(), SafebooruSource(), E621Source(),
        PixivSource(), TumblrSource(), BlueskySource(), DeviantArtSource(),
    ).associateBy(SourceClient::source)

    suspend fun search(
        category: Category,
        sources: Set<ArtSource>,
        pages: Int,
        credentials: Map<String, String>,
    ): SearchOutcome = supervisorScope {
        val results = sources.mapNotNull { source -> clients[source]?.let { source to it } }.map { (source, client) ->
            async {
                runCatching { client.search(category, pages.coerceIn(1, 5), credentials) }
                    .fold({ Triple(source, it, null) }, { Triple(source, emptyList(), friendlyError(it, credentials)) })
            }
        }.awaitAll()
        SearchOutcome(
            posts = results.flatMap { it.second }.distinctBy { "${it.source.id}:${it.id}" }
                .sortedByDescending { it.score },
            errors = results.mapNotNull { (source, _, error) -> error?.let { source to it } }.toMap(),
        )
    }

    private fun friendlyError(error: Throwable, credentials: Map<String, String>): String {
        val message = generateSequence(error) { it.cause }.mapNotNull(Throwable::message).firstOrNull()
        val redacted = credentials.values.filter { it.length >= 4 }.fold(message.orEmpty()) { current, secret ->
            current.replace(secret, "[protegido]")
        }
        return redacted.take(220).ifBlank { "A fonte não respondeu." }
    }
}
