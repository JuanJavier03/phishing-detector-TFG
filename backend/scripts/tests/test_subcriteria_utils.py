from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from utils.subcriteria_utils import normalize_subcriterion_result, store_subcriterion_result


class SubcriteriaUtilsTests(unittest.TestCase):
    def test_normalizes_and_stores_subcriterion_result(self) -> None:
        email = {"enrichment": {}}
        result = {"criterion": "criterio1.spf", "score": 1, "detail": {"method": "local"}}

        changed = store_subcriterion_result(email, result)
        normalized = normalize_subcriterion_result(result)

        self.assertTrue(changed)
        self.assertEqual(normalized["criterion_key"], "spf")
        self.assertEqual(email["enrichment"]["spf"]["value"], 1)


if __name__ == "__main__":
    unittest.main()
