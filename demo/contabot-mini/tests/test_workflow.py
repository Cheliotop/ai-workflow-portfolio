from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from contabot_demo import (
    add_review_decision,
    build_export,
    parse_invoice,
    process_invoice,
)


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rDE>
  <DE Id="01800123456001001000012342026010112345678901">
    <gTimb><dNumTim>12345678</dNumTim></gTimb>
    <dTipoDoc>1</dTipoDoc>
    <dNumDoc>001-001-0001234</dNumDoc>
    <dFeEmiDE>2026-07-13T09:30:00</dFeEmiDE>
    <dMoneda>PYG</dMoneda>
    <gEmis><dRucEm>80012345-6</dRucEm><dNomEmi>Proveedor Demo S.A.</dNomEmi></gEmis>
    <gRecp><dNomRec>Cliente de Ejemplo</dNomRec></gRecp>
    <gCamItem>
      <dCodInt>DEMO-01</dCodInt><dDesProSer>Servicio de ejemplo</dDesProSer>
      <dCantProSer>1</dCantProSer><dPUniProSer>100000</dPUniProSer>
      <dTotOpeItem>110000</dTotOpeItem><dIVAItem>10000</dIVAItem>
      <iAfecIVA>1</iAfecIVA><dTasaIVA>10</dTasaIVA>
    </gCamItem>
    <gTotSub><dSubGrav>100000</dSubGrav><dTotIVA>10000</dTotIVA><dTotGralOpe>110000</dTotGralOpe></gTotSub>
  </DE>
</rDE>
"""


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.xml_path = Path(self.temp_dir.name) / "sample-invoice.xml"
        self.xml_path.write_text(SAMPLE_XML, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parse_invoice_extracts_traceable_business_fields(self) -> None:
        record = parse_invoice(self.xml_path)

        self.assertEqual(record["document_number"], "001-001-0001234")
        self.assertEqual(record["issuer"]["name"], "Proveedor Demo S.A.")
        self.assertEqual(record["totals"]["grand_total"], 110000)
        self.assertEqual(record["items"][0]["description"], "Servicio de ejemplo")
        self.assertEqual(len(record["source_sha256"]), 64)

    def test_missing_receiver_tax_id_routes_record_to_review(self) -> None:
        result = process_invoice(self.xml_path)

        self.assertEqual(result["base_status"], "needs_review")
        self.assertEqual(result["review_state"], "pending")
        self.assertEqual(result["workflow_state"], "review_pending")
        self.assertIn("missing_receiver_tax_id", result["reason_codes"])

    def test_approval_is_appended_without_changing_base_status(self) -> None:
        result = process_invoice(self.xml_path)
        original_status = result["base_status"]

        reviewed = add_review_decision(result, "approve", "demo-reviewer")

        self.assertEqual(reviewed["base_status"], original_status)
        self.assertEqual(reviewed["review_state"], "approved")
        self.assertEqual(reviewed["workflow_state"], "review_approved")
        self.assertEqual(len(reviewed["decision_history"]), 1)
        self.assertEqual(reviewed["decision_history"][0]["action"], "approve")

    def test_invalid_review_action_is_rejected(self) -> None:
        result = process_invoice(self.xml_path)

        with self.assertRaisesRegex(ValueError, "unsupported review action"):
            add_review_decision(result, "delete", "demo-reviewer")

    def test_export_contains_audit_summary_and_no_raw_xml(self) -> None:
        result = add_review_decision(
            process_invoice(self.xml_path), "approve", "demo-reviewer"
        )

        exported = build_export(result)
        encoded = json.dumps(exported)

        self.assertEqual(exported["workflow_state"], "review_approved")
        self.assertEqual(exported["decision_count"], 1)
        self.assertNotIn("<rDE>", encoded)


if __name__ == "__main__":
    unittest.main()
