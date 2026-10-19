package io.github.gabizips.artfinder.data

import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import okhttp3.Call
import okhttp3.Response
import java.io.InputStream
import java.io.OutputStream

/** Bounded memory and output even when Content-Length is absent or dishonest. */
internal fun copyBounded(
    input: InputStream,
    output: OutputStream,
    maxBytes: Long,
    checkActive: () -> Unit = {},
): Long {
    require(maxBytes >= 0)
    val buffer = ByteArray(16 * 1024)
    var total = 0L
    while (true) {
        checkActive()
        // Read at most one byte past the limit, solely to detect overflow.
        val count = input.read(buffer, 0, minOf(buffer.size.toLong(), maxBytes - total + 1).toInt())
        if (count < 0) return total
        checkActive()
        require(count.toLong() <= maxBytes - total) { "O arquivo excede o limite de $maxBytes bytes." }
        output.write(buffer, 0, count)
        total += count
    }
}

/** Cancel closes the socket while execute/read is blocked on an IO thread. */
internal suspend fun <T> Call.useCancellable(block: (Response) -> T): T = withContext(Dispatchers.IO) {
    coroutineScope {
        val cancellation = launch(Dispatchers.Unconfined, start = CoroutineStart.UNDISPATCHED) {
            try { awaitCancellation() } finally { this@useCancellable.cancel() }
        }
        try {
            ensureActive()
            execute().use(block)
        } catch (error: Exception) {
            ensureActive()
            throw error
        } finally {
            cancellation.cancel()
        }
    }
}

/** Same-key callers re-check persisted state serially; distinct keys share a transfer limit. */
internal class TransferCoordinator(maxConcurrent: Int = 3) {
    private class Entry(val mutex: Mutex = Mutex(), var users: Int = 0)
    private val entries = mutableMapOf<String, Entry>()
    private val permits = Semaphore(maxConcurrent)

    suspend fun <T> run(key: String, block: suspend () -> T): T {
        val entry = synchronized(entries) { entries.getOrPut(key) { Entry() }.also { it.users++ } }
        try {
            return entry.mutex.withLock { permits.withPermit { block() } }
        } finally {
            synchronized(entries) {
                if (--entry.users == 0) entries.remove(key)
            }
        }
    }
}

internal suspend fun deleteThenForget(deleteFile: () -> Int, forget: suspend () -> Unit) {
    check(deleteFile() > 0) { "Não foi possível excluir a imagem do dispositivo. O registro foi mantido." }
    forget()
}
