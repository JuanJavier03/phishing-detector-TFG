from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from enrichment.mcdm_score_helper import compute_mcdm_block_for_email_with_hardcoded_references, field_unit_score
from enrichment.vector_schema import VECTOR_FIELD_ORDER


class McdmScoreTests(unittest.TestCase):
    def test_converts_raw_values_to_unit_scores(self) -> None:
        self.assertEqual(field_unit_score("c1_spf", 1), 1.0)
        self.assertEqual(field_unit_score("c1_spf", 0), 0.0)
        self.assertEqual(field_unit_score("c1_spf", None), 0.5)

    def test_single_email_uses_hardcoded_reference_vectors(self) -> None:
        by_key = {field: 0.0 for field in VECTOR_FIELD_ORDER}
        email = {
            "numeric_values": {
                "version": 6,
                "fields": list(VECTOR_FIELD_ORDER),
                "values": [by_key[field] for field in VECTOR_FIELD_ORDER],
                "by_key": by_key,
            }
        }

        block = compute_mcdm_block_for_email_with_hardcoded_references(email)

        self.assertEqual(block["method"], "topsis_with_phishpot1050_extreme_references_scaled")
        self.assertEqual(block["comparison_count"], 1)
        self.assertEqual(block["reference_count"], 2)
        self.assertEqual(block["internal_matrix_count"], 3)
        self.assertTrue(block["uses_reference_anchors"])
        self.assertEqual(block["reference_source"], "Phishpot1050")


if __name__ == "__main__":
    unittest.main()
