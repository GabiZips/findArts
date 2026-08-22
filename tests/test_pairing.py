import json
import urllib.error
import urllib.request
import unittest

from utils import pairing


class PairingCryptoTests(unittest.TestCase):
    def test_code_keeps_key_out_of_endpoint_and_round_trips_payload(self):
        payload = {
            "version": 1,
            "sections": {"categories": True, "credentials": True},
            "categories": {"vex": {"tags": "vex_(league_of_legends)"}},
            "credentials": {"PIXIV_REFRESH_TOKEN": "secret-token"},
        }
        session = pairing.PairingSession(payload, addresses=["127.0.0.1"])
        try:
            option = session.options[0]
            descriptor = pairing.parse_pairing_code(option["code"])
            self.assertNotIn(descriptor["key"], descriptor["url"])
            self.assertEqual(set(option), {"address", "code"})

            with urllib.request.urlopen(descriptor["url"], timeout=2) as response:
                envelope = json.loads(response.read())
            self.assertNotIn(descriptor["key"], json.dumps(envelope))

            decoded = pairing.decrypt_payload(
                envelope,
                pairing._b64decode(descriptor["key"]),
            )
            self.assertEqual(decoded, payload)
        finally:
            session.close()

    def test_pairing_endpoint_is_single_use(self):
        session = pairing.PairingSession(
            {"version": 1},
            addresses=["127.0.0.1"],
        )
        try:
            endpoint = pairing.parse_pairing_code(session.options[0]["code"])["url"]
            with urllib.request.urlopen(endpoint, timeout=2) as response:
                self.assertEqual(response.status, 200)
            with self.assertRaises(urllib.error.HTTPError) as captured:
                urllib.request.urlopen(endpoint, timeout=2)
            self.assertEqual(captured.exception.code, 410)
        finally:
            session.close()

    def test_expired_pairing_endpoint_rejects_download(self):
        now = [10.0]
        session = pairing.PairingSession(
            {"version": 1},
            ttl_seconds=10,
            addresses=["127.0.0.1"],
            clock=lambda: now[0],
        )
        try:
            now[0] = 21.0
            endpoint = pairing.parse_pairing_code(session.options[0]["code"])["url"]
            with self.assertRaises(urllib.error.HTTPError) as captured:
                urllib.request.urlopen(endpoint, timeout=2)
            self.assertEqual(captured.exception.code, 410)
        finally:
            session.close()

    def test_wrong_key_cannot_decrypt(self):
        key = bytes(range(32))
        nonce = bytes(range(12))
        ciphertext = pairing.encrypt_payload({"version": 1}, key, nonce)
        envelope = {
            "version": 1,
            "algorithm": "AES-256-GCM",
            "nonce": pairing._b64encode(nonce),
            "ciphertext": pairing._b64encode(ciphertext),
        }
        with self.assertRaises(pairing.PairingError):
            pairing.decrypt_payload(envelope, b"x" * 32)

    def test_malformed_code_is_rejected(self):
        with self.assertRaises(pairing.PairingError):
            pairing.parse_pairing_code("https://example.test/not-a-pairing-code")


if __name__ == "__main__":
    unittest.main()
