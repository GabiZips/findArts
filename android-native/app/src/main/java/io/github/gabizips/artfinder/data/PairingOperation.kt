package io.github.gabizips.artfinder.data

import kotlinx.coroutines.CancellationException

internal suspend fun runPairingOperation(
    setBusy: (Boolean) -> Unit,
    onFailure: (Exception) -> Unit,
    operation: suspend () -> Unit,
) {
    setBusy(true)
    try {
        operation()
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (error: Exception) {
        onFailure(error)
    } finally {
        setBusy(false)
    }
}
