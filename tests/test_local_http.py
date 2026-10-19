"""Real loopback HTTP smoke test, with no accounts or external API calls."""

import socket
import threading
import time
import unittest
from unittest.mock import patch

import requests
import uvicorn
import app


class LocalHttpTests(unittest.TestCase):
    def test_bootstrap_cookie_unlocks_api_and_host_check_precedes_session(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(app.app, log_level="critical", access_log=False))
        worker = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
        with patch.dict(app.os.environ, {"ARTFINDER_LAN": "0"}), \
             patch.object(app, "_load_user_cats", return_value={}):
            worker.start()
            try:
                deadline = time.monotonic() + 8
                while not server.started and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(server.started)
                with requests.Session() as client:
                    client.trust_env = False
                    self.assertEqual(client.get(url + "/api/categories", timeout=3).status_code, 401)
                    self.assertEqual(client.get(url + "/", timeout=3).status_code, 200)
                    self.assertEqual(client.get(url + "/api/categories", timeout=3).status_code, 200)
                    self.assertEqual(client.get(url + "/ui/viewer.js", timeout=3).status_code, 200)
                    self.assertEqual(client.get(url + "/api/categories", headers={"Host": "untrusted.example"}, timeout=3).status_code, 400)
            finally:
                server.should_exit = True
                worker.join(8)
                listener.close()
        self.assertFalse(worker.is_alive())
