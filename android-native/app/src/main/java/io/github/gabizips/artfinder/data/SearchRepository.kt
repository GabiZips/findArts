package io.github.gabizips.artfinder.data

import io.github.gabizips.artfinder.data.source.BlueskySource
import io.github.gabizips.artfinder.data.source.DanbooruSource
import io.github.gabizips.artfinder.data.source.DeviantArtSource
import io.github.gabizips.artfinder.data.source.E621Source
import io.github.gabizips.artfinder.data.source.GelbooruSource
import io.github.gabizips.artfinder.data.source.PixivSource
import io.github.gabizips.artfinder.data.source.RequestTracker
import io.github.gabizips.artfinder.data.source.SafebooruSource
import io.github.gabizips.artfinder.data.source.SourceClient
import io.github.gabizips.artfinder.data.source.TumblrSource
import io.github.gabizips.artfinder.data.source.containsAi
import io.github.gabizips.artfinder.data.source.queriesFor
import io.github.gabizips.artfinder.model.ArtPost
import io.github.gabizips.artfinder.model.ArtSource
import io.github.gabizips.artfinder.model.Category
import io.github.gabizips.artfinder.model.SearchOptions
import io.github.gabizips.artfinder.model.SearchOutcome
import io.github.gabizips.artfinder.model.SearchProgress
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.supervisorScope

class SearchRepository {
    private val clients: Map<ArtSource, SourceClient> = listOf(
        DanbooruSource(), GelbooruSource(), SafebooruSource(), E621Source(),
        PixivSource(), TumblrSource(), BlueskySource(), DeviantArtSource(),
    ).associateBy(SourceClient::source)

    fun estimateRequestCount(category: Category, sources: Set<ArtSource>, pages: Int): Int {
        val safePages = pages.coerceIn(1, 25)
        val dataRequests = sources.sumOf { source ->
            category.queriesFor(source).distinct().size.coerceAtLeast(1) * safePages
        }
        val authenticationRequests = sources.count {
            it == ArtSource.PIXIV || it == ArtSource.BLUESKY || it == ArtSource.DEVIANTART
        }
        return dataRequests + authenticationRequests
    }

    suspend fun search(
        category: Category,
        sources: Set<ArtSource>,
        options: SearchOptions,
        credentials: Map<String, String>,
        onProgress: (SearchProgress) -> Unit = {},
    ): SearchOutcome = supervisorScope {
        val safeOptions = options.copy(pages = options.pages.coerceIn(1, 25), minScore = options.minScore.coerceAtLeast(0))
        val completedSources = AtomicInteger(0)
        val tracker = RequestTracker { requestCount ->
            onProgress(SearchProgress(requestCount, completedSources.get(), sources.size))
        }
        onProgress(SearchProgress(totalSources = sources.size))
        val results = sources.mapNotNull { source -> clients[source]?.let { source to it } }.map { (source, client) ->
            async {
                try {
                    Triple(source, client.search(category, safeOptions, credentials, tracker), null)
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (error: Throwable) {
                    Triple(source, emptyList(), friendlyError(error, credentials))
                } finally {
                    val completed = completedSources.incrementAndGet()
                    onProgress(SearchProgress(tracker.count, completed, sources.size))
                }
            }
        }.awaitAll()
        val uniquePosts = results.flatMap { it.second }.distinctBy { "${it.source.id}:${it.id}" }
        SearchOutcome(
            posts = uniquePosts.sortedByDescending(ArtPost::score),
            errors = results.mapNotNull { (source, _, error) -> error?.let { source to it } }.toMap(),
            requestCount = tracker.count,
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

internal fun applySearchOptions(
    posts: List<ArtPost>,
    options: SearchOptions,
    nowEpochSeconds: Long = System.currentTimeMillis() / 1000,
): List<ArtPost> {
    val cutoff = options.periodDays.takeIf { it > 0 }?.let { nowEpochSeconds - it * 86_400L }
    return posts.asSequence()
        .filter { post ->
            when (post.rating.lowercase()) {
                "nsfw", "explicit", "e" -> options.includeNsfw
                "sensitive", "questionable", "q", "s" -> options.includeSensitive
                else -> options.includeSfw
            }
        }
        .filter { it.score >= options.minScore }
        .filter { cutoff == null || (it.postDate > 0 && it.postDate >= cutoff) }
        .filterNot { options.hideAi && (it.isAi || containsAi(it.tags)) }
        .sortedByDescending(ArtPost::score)
        .toList()
}
