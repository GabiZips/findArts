package io.github.gabizips.artfinder.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.util.Base64

class PairingRepositoryTest {
    private val repository = PairingRepository()

    @Test
    fun acceptsPrivateLanPairingEndpoint() {
        assertEquals(
            "192.168.1.20",
            repository.validateEndpoint("http://192.168.1.20:43117/v1/pair/random-token").host,
        )
    }

    @Test
    fun rejectsPublicOrLoopbackEndpoints() {
        listOf(
            "http://8.8.8.8:43117/v1/pair/token",
            "http://127.0.0.1:43117/v1/pair/token",
            "https://192.168.1.20:43117/v1/pair/token",
            "http://192.168.1.20:43117/other/token",
            "http://user@192.168.1.20:43117/v1/pair/token",
        ).forEach { endpoint ->
            assertThrows(IllegalArgumentException::class.java) { repository.validateEndpoint(endpoint) }
        }
    }

    @Test
    fun acceptsAllRfc1918Ranges() {
        listOf("10.0.0.2", "172.16.0.2", "172.31.255.2", "192.168.50.2").forEach { host ->
            assertEquals(host, repository.validateEndpoint("http://$host:8080/v1/pair/token").host)
        }
    }

    @Test
    fun decryptsEnvelopeCreatedByDesktopPythonProtocol() {
        val envelope = """{"version":1,"algorithm":"AES-256-GCM","nonce":"AAECAwQFBgcICQoL","ciphertext":"PCCgfreWq3TjY626ncsLCOCi7lueCH1GQ0WG5GkMZ91zecuPjftm6gHBU8_r9U1cizcU5Du60PgF41hsfZ7ZzJNdsh-0vlQIeSeIVJSteI1A1aUNGkFpE9-R_64dnJu36a48noZt6m7_e02QcldXGsI4SseGpELvKKA4q92KC2nePGS1nfXncXuOPdNevxO2V5OQFw9qsTrlJ4EB2OiyzHAUKvZrWC_9JIBfVTwCP5nAs7dfp4kQzgC7pakFrNafYG6wgS-Nn5F-AIy0_weLwbI2pyJyS_-_U6u4syQ7-9c3TL_KiAJ-WFoMNsfNvVLzpPDYRNYj56s"}"""
        val key = Base64.getUrlDecoder().decode("AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8")
        val imported = repository.decryptEnvelope(envelope, key)
        assertEquals("Vex", imported.categories?.single()?.label)
        assertEquals(listOf("ヴェックス"), imported.categories?.single()?.sourceTags?.get("pixiv"))
        assertEquals("test-token", imported.credentials["PIXIV_REFRESH_TOKEN"])
    }
}
