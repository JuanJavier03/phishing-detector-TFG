from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from parse_emails import parse_email_bytes, sha256_bytes


class ParseEmailBytesTests(unittest.TestCase):
    def test_extracts_basic_headers_body_and_html_url(self) -> None:
        raw = (
            b"From: Alice <alice@example.com>\r\n"
            b"To: Bob <bob@example.net>\r\n"
            b"Subject: Aviso urgente\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"\r\n"
            b'<html><body>Accede <a href="https://login.example.com/pay">aqui</a></body></html>'
        )

        parsed = parse_email_bytes(
            raw=raw,
            file_name="sample.eml",
            file_path_rel="phishpot/sample.eml",
            raw_sha=sha256_bytes(raw),
            raw_size=len(raw),
        )

        self.assertEqual(parsed["headers"]["subject"], "Aviso urgente")
        self.assertIn("https://login.example.com/pay", {item["url"] for item in parsed["urls"]})
        self.assertEqual(parsed["metadata"]["file_ext"], ".eml")


if __name__ == "__main__":
    unittest.main()
