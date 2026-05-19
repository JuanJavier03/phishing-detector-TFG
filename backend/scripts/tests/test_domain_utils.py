from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from utils.domain_utils import base_domain, normalize_host


class DomainUtilsTests(unittest.TestCase):
    def test_normalizes_host_and_extracts_registrable_domain(self) -> None:
        self.assertEqual(normalize_host(" Mail.Example.COM:443 "), "mail.example.com")
        self.assertEqual(base_domain("login.universidad.com.es"), "universidad.com.es")
        self.assertIsNone(normalize_host("https://example.com/path"))


if __name__ == "__main__":
    unittest.main()
