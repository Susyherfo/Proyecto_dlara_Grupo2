import json
from http.server import ThreadingHTTPServer
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from api_server import ProjectRequestHandler


class ProjectAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ProjectRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_dashboard_contains_cleaning_results_and_api_image_urls(self):
        with urlopen(f"{self.base_url}/api/dashboard") as response:
            payload = json.load(response)

        self.assertEqual(len(payload["fotos"]), 409)
        self.assertEqual(payload["estadisticas"]["conservadas"], 176)
        self.assertEqual(payload["estadisticas"]["descartadas"], 233)
        self.assertEqual(sum(photo["rev"] for photo in payload["fotos"]), 7)
        first_kept = next(photo for photo in payload["fotos"] if photo["d"] == "CONSERVADA")
        self.assertRegex(first_kept["p"], r"^/api/photos/\d+/image$")

    def test_image_route_serves_only_a_registered_photo(self):
        with urlopen(f"{self.base_url}/api/dashboard") as response:
            payload = json.load(response)
        photo = next(photo for photo in payload["fotos"] if photo["p"])

        with urlopen(f"{self.base_url}{photo['p']}") as response:
            self.assertEqual(response.headers.get_content_type(), "image/jpeg")
            self.assertTrue(response.read(2).startswith(b"\xff\xd8"))

        with self.assertRaises(HTTPError) as missing:
            urlopen(f"{self.base_url}/api/photos/999999/image")
        self.assertEqual(missing.exception.code, 404)

        discarded = next(photo for photo in payload["fotos"] if photo["p"] is None)
        with self.assertRaises(HTTPError) as unavailable:
            urlopen(f"{self.base_url}/api/photos/{discarded['id']}/image")
        self.assertEqual(unavailable.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
