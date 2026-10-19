package io.github.gabizips.artfinder.data

import io.github.gabizips.artfinder.model.Category
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.net.URI
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

data class PairingImport(val categories: List<Category>?, val credentials: Map<String, String>)

class PairingRepository(
    client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(4, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .callTimeout(12, TimeUnit.SECONDS)
        .build(),
) {
    // Also harden injected clients: endpoint validation must never be bypassed by a redirect.
    private val client = client.newBuilder().followRedirects(false).followSslRedirects(false).build()

    suspend fun receive(code: String): PairingImport = withContext(Dispatchers.IO) {
        require(code.length <= 12_000 && code.startsWith(PREFIX)) { "Código de pareamento inválido." }
        val descriptor = JSONObject(decode(code.removePrefix(PREFIX)).toString(Charsets.UTF_8))
        val endpoint = validateEndpoint(descriptor.getString("url"))
        val key = decode(descriptor.getString("key"))
        require(key.size == 32) { "Código de pareamento inválido." }

        val request = Request.Builder().url(endpoint.toString()).header("Accept", "application/json").build()
        val coroutineContext = currentCoroutineContext()
        val body = client.newCall(request).useCancellable { response ->
            when {
                response.code == 410 -> error("O código expirou ou já foi utilizado.")
                !response.isSuccessful -> error("O PC recusou o pareamento (${response.code}).")
                else -> {
                    require(response.body.contentLength() <= MAX_RESPONSE_BYTES) { "Resposta de pareamento inválida." }
                    val output = ByteArrayOutputStream()
                    response.body.byteStream().use { input ->
                        copyBounded(input, output, MAX_RESPONSE_BYTES) { coroutineContext.ensureActive() }
                    }
                    output.toString(Charsets.UTF_8.name())
                }
            }
        }
        decryptEnvelope(body, key)
    }

    internal fun decryptEnvelope(body: String, key: ByteArray): PairingImport {
        val envelope = JSONObject(body)
        require(envelope.optInt("version") == 1 && envelope.optString("algorithm") == "AES-256-GCM") {
            "Pacote de pareamento incompatível."
        }
        val nonce = decode(envelope.getString("nonce"))
        require(nonce.size == 12) { "Pacote de pareamento inválido." }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
        cipher.updateAAD(AAD)
        val payload = JSONObject(cipher.doFinal(decode(envelope.getString("ciphertext"))).toString(Charsets.UTF_8))
        return validatePayload(payload)
    }

    internal fun validateEndpoint(raw: String): URI {
        val uri = URI(raw)
        require(uri.scheme == "http" && uri.userInfo == null && uri.fragment == null) { "Endereço de pareamento inválido." }
        require(uri.path.startsWith("/v1/pair/") && uri.query == null) { "Endereço de pareamento inválido." }
        require(uri.port in 1..65535 && isPrivateIpv4(uri.host.orEmpty())) { "O pareamento deve usar o IP privado do PC." }
        return uri
    }

    private fun validatePayload(payload: JSONObject): PairingImport {
        require(payload.optInt("version") == 1) { "Configuração incompatível." }
        val sections = payload.optJSONObject("sections") ?: error("Configuração inválida.")
        val categories = if (sections.optBoolean("categories")) {
            val objectValue = payload.optJSONObject("categories") ?: JSONObject()
            require(objectValue.length() <= 500) { "Muitas categorias no pareamento." }
            JsonCodec.categoriesFromJson(objectValue.toString())
        } else null
        val credentials = if (sections.optBoolean("credentials")) {
            val objectValue = payload.optJSONObject("credentials") ?: JSONObject()
            objectValue.keys().asSequence().associateWith { key ->
                require(key in SettingsRepository.ALLOWED_CREDENTIALS) { "Credencial desconhecida." }
                objectValue.getString(key).also { value ->
                    require(value.length <= 4096 && value.none { it == '\n' || it == '\r' || it == '\u0000' })
                }
            }.filterValues(String::isNotBlank)
        } else emptyMap()
        require(categories != null || credentials.isNotEmpty()) { "O pacote não contém dados importáveis." }
        return PairingImport(categories, credentials)
    }

    private fun isPrivateIpv4(host: String): Boolean {
        val parts = host.split('.').mapNotNull(String::toIntOrNull)
        if (parts.size != 4 || parts.any { it !in 0..255 }) return false
        return parts[0] == 10 ||
            (parts[0] == 172 && parts[1] in 16..31) ||
            (parts[0] == 192 && parts[1] == 168)
    }

    private fun decode(value: String): ByteArray = Base64.getUrlDecoder().decode(value)

    companion object {
        internal const val MAX_RESPONSE_BYTES = 600_000L
        const val PREFIX = "artfinder-pair:v1:"
        val AAD = "ArtFinder pairing v1".toByteArray(Charsets.UTF_8)
    }
}
