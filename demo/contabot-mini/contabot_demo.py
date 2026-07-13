#!/usr/bin/env python3
"""Public-safe miniature of an auditable XML review workflow.

This demo is intentionally small and uses fake data. It illustrates workflow
invariants from the private ContaBot project; it is not tax or compliance software.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _text(root: ET.Element, tag: str) -> Optional[str]:
    element = root.find(f".//{tag}")
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _number(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def parse_invoice(xml_path: Path) -> dict[str, Any]:
    """Parse a bounded set of fields and preserve a source checksum."""
    path = Path(xml_path)
    root = ET.parse(path).getroot()
    de = root.find(".//DE")

    items = []
    for index, item in enumerate(root.findall(".//gCamItem"), start=1):
        items.append(
            {
                "line_no": index,
                "code": _text(item, "dCodInt"),
                "description": _text(item, "dDesProSer"),
                "quantity": _number(_text(item, "dCantProSer")),
                "unit_price": _number(_text(item, "dPUniProSer")),
                "line_total": _number(_text(item, "dTotOpeItem")),
                "tax_amount": _number(_text(item, "dIVAItem")),
                "tax_rate_pct": _number(_text(item, "dTasaIVA")),
                "source_pointer": f"/rDE/DE/gCamItem[{index}]",
            }
        )

    return {
        "source_file": path.name,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cdc": de.get("Id") if de is not None else None,
        "timbrado": _text(root, "dNumTim"),
        "document_type": _text(root, "dTipoDoc"),
        "document_number": _text(root, "dNumDoc"),
        "issued_at": _text(root, "dFeEmiDE"),
        "currency": _text(root, "dMoneda"),
        "issuer": {"tax_id": _text(root, "dRucEm"), "name": _text(root, "dNomEmi")},
        "receiver": {"tax_id": _text(root, "dRucRec"), "name": _text(root, "dNomRec")},
        "items": items,
        "totals": {
            "subtotal": _number(_text(root, "dSubGrav")),
            "tax_total": _number(_text(root, "dTotIVA")),
            "grand_total": _number(_text(root, "dTotGralOpe")),
        },
    }


def validate_invoice(record: dict[str, Any]) -> list[str]:
    """Return explicit reason codes instead of guessing missing values."""
    checks = {
        "missing_document_number": record.get("document_number"),
        "missing_issuer_tax_id": record.get("issuer", {}).get("tax_id"),
        "missing_receiver_tax_id": record.get("receiver", {}).get("tax_id"),
        "missing_grand_total": record.get("totals", {}).get("grand_total"),
        "missing_line_items": record.get("items"),
    }
    return [reason for reason, value in checks.items() if value in (None, "", [])]


def process_invoice(xml_path: Path) -> dict[str, Any]:
    """Parse and validate while keeping base and review state separate."""
    record = parse_invoice(xml_path)
    reason_codes = validate_invoice(record)
    base_status = "needs_review" if reason_codes else "accepted"
    workflow_state = "review_pending" if base_status == "needs_review" else "completed_accepted"
    return {
        "record": record,
        "base_status": base_status,
        "reason_codes": reason_codes,
        "review_state": "pending",
        "workflow_state": workflow_state,
        "decision_history": [],
    }


def add_review_decision(
    result: dict[str, Any], action: str, reviewer_id: str
) -> dict[str, Any]:
    """Append a decision while preserving the immutable processing result."""
    if action not in {"approve", "reject", "leave_pending"}:
        raise ValueError("unsupported review action")
    if result.get("base_status") != "needs_review":
        raise ValueError("record is not reviewable in current workflow state")

    updated = copy.deepcopy(result)
    updated["decision_history"].append(
        {
            "action": action,
            "reviewer_id": reviewer_id,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "reason_codes_at_decision": list(updated.get("reason_codes", [])),
        }
    )
    updated["review_state"] = {
        "approve": "approved",
        "reject": "rejected",
        "leave_pending": "pending",
    }[action]
    updated["workflow_state"] = {
        "approve": "review_approved",
        "reject": "review_rejected",
        "leave_pending": "review_pending",
    }[action]
    return updated


def build_export(result: dict[str, Any]) -> dict[str, Any]:
    """Create a bounded audit summary without embedding raw XML."""
    record = result["record"]
    return {
        "document_number": record["document_number"],
        "source_sha256": record["source_sha256"],
        "issuer_name": record["issuer"]["name"],
        "receiver_name": record["receiver"]["name"],
        "currency": record["currency"],
        "grand_total": record["totals"]["grand_total"],
        "base_status": result["base_status"],
        "reason_codes": result["reason_codes"],
        "review_state": result["review_state"],
        "workflow_state": result["workflow_state"],
        "decision_count": len(result["decision_history"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml_file", type=Path)
    parser.add_argument("--decision", choices=("approve", "reject", "leave_pending"))
    parser.add_argument("--reviewer", default="demo-reviewer")
    args = parser.parse_args()

    result = process_invoice(args.xml_file)
    if args.decision:
        result = add_review_decision(result, args.decision, args.reviewer)
    print(json.dumps(build_export(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
