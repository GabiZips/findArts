package io.github.gabizips.artfinder.data

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class TransferSafetyTest {
    @Test fun boundedCopyAcceptsExactLimitAndRejectsOverflowBeforeWriting() {
        val output = ByteArrayOutputStream()
        assertEquals(12L, copyBounded(ByteArrayInputStream(ByteArray(12)), output, 12))
        assertEquals(12, output.size())
        val overflow = ByteArrayOutputStream()
        assertThrows(IllegalArgumentException::class.java) {
            copyBounded(ByteArrayInputStream(ByteArray(13)), overflow, 12)
        }
        assertTrue(overflow.size() <= 12)
    }

    @Test fun cancelledCopyStopsBeforeReading() {
        val output = ByteArrayOutputStream()
        assertThrows(CancellationException::class.java) {
            copyBounded(ByteArrayInputStream(ByteArray(20)), output, 20) { throw CancellationException() }
        }
        assertEquals(0, output.size())
    }

    @Test fun failedDeletionDoesNotForgetRecord() = runBlocking {
        var forgotten = false
        try {
            deleteThenForget({ throw IOException("denied") }, { forgotten = true })
            fail("Expected deletion error")
        } catch (_: IOException) { }
        assertFalse(forgotten)
        try {
            deleteThenForget({ 0 }, { forgotten = true })
            fail("Expected zero-row error")
        } catch (_: IllegalStateException) { }
        assertFalse(forgotten)
        deleteThenForget({ 1 }, { forgotten = true })
        assertTrue(forgotten)
    }

    @Test fun coordinatorLimitsConcurrencyAndSerializesSameArtwork() = runBlocking {
        for (sameKey in listOf(false, true)) {
            val coordinator = TransferCoordinator(3)
            val active = AtomicInteger()
            val peak = AtomicInteger()
            (0 until 9).map { index ->
                async {
                    coordinator.run(if (sameKey) "same" else index.toString()) {
                        val count = active.incrementAndGet()
                        peak.updateAndGet { maxOf(it, count) }
                        delay(10)
                        active.decrementAndGet()
                    }
                }
            }.awaitAll()
            assertTrue(peak.get() <= if (sameKey) 1 else 3)
            assertEquals(0, active.get())
        }
    }

    @Test fun persistenceFailureClearsPairingBusyAndCancellationPropagates() = runBlocking {
        val states = mutableListOf<Boolean>()
        var error: Exception? = null
        runPairingOperation({ states += it }, { error = it }) { throw IOException("save failed") }
        assertEquals(listOf(true, false), states)
        assertTrue(error is IOException)
        states.clear()
        try {
            runPairingOperation({ states += it }, { fail("Cancellation was swallowed") }) { throw CancellationException() }
            fail("Cancellation should propagate")
        } catch (_: CancellationException) { }
        assertEquals(listOf(true, false), states)
    }
}
