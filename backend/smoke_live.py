"""Live HTTP smoke test against a running uvicorn server.

Exercises the real API over the network rather than through an in-process test
client, so routing, serialisation, and status codes are genuinely checked.

Run with the server already listening, e.g.
    uvicorn app.main:app --host 127.0.0.1 --port 8000
    python smoke_live.py
"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"

results: list[bool] = []


def call(method: str, path: str, payload: dict | None = None) -> tuple[int, object]:
    """Make an HTTP request and return ``(status, parsed_body)``."""
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}


def check(label: str, condition: bool, detail: str = "") -> bool:
    """Print one PASS/FAIL line and record it."""
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}{(' -> ' + detail) if detail else ''}")
    results.append(bool(condition))
    return bool(condition)


print("1. Health and reference data")
status, health = call("GET", "/health")
check("GET /health returns 200", status == 200, str(status))
check("database connected", health.get("database") == "connected")
check("provider is mock", health.get("ai_provider") == "mock")

status, langs = call("GET", "/languages")
check("GET /languages returns 200", status == 200)
check(
    "three target languages",
    len(langs.get("targets", [])) == 3,
    ",".join(t["code"] for t in langs.get("targets", [])),
)

status, levels = call("GET", "/risk-levels")
check("GET /risk-levels returns 200", status == 200)
check("three risk tiers", len(levels.get("levels", [])) == 3)

status, examples = call("GET", "/examples")
check("GET /examples returns 200", status == 200)
check(
    "examples are de-identified",
    all("mramirez" not in item.get("source_message", "").lower() for item in examples.get("items", [])),
)

print("\n2. The approval gate")
source = (
    "Students are expected to return the field trip permission form in a timely manner. "
    "The form should be signed by a parent and returned to your child's teacher by "
    "Friday, September 18. Contact the undersigned with inquiries. Your cooperation "
    "is appreciated. If you need an interpreter, please call the program office at "
    "+1-555-0100."
)

status, created = call(
    "POST",
    "/messages",
    {
        "source_message": source,
        "audience": "families",
        "purpose": "Collect permission forms",
        "action": "Return the signed form",
        "deadline": "Friday, September 18",
        "risk_level": "routine",
        "target_languages": ["es", "hi"],
    },
)
check("POST /messages returns 201", status == 201, str(status))
message_id = created.get("id", "")
check("message starts in draft", created.get("state") == "draft")

status, denied = call(
    "POST", "/translations", {"message_id": message_id, "target_languages": ["es", "hi"]}
)
code = denied.get("error", {}).get("code") if isinstance(denied, dict) else ""
check(
    "translation refused before approval",
    status == 409 and code == "SOURCE_NOT_APPROVED",
    f"{status} {code}",
)

print("\n3. Rewrite")
status, rewrite = call("POST", "/messages/rewrite", {"message_id": message_id})
check("POST /messages/rewrite returns 200", status == 200, str(status))
check(
    "changes are explained",
    len(rewrite.get("changes", [])) > 0,
    f"{len(rewrite.get('changes', []))} changes",
)
check(
    "ambiguity is surfaced",
    len(rewrite.get("open_questions", [])) > 0,
    f"{len(rewrite.get('open_questions', []))} questions",
)

print("\n4. Approve and translate")
status, approved = call(
    "POST", f"/messages/{message_id}/approve", {"approved": True, "reviewer": "smoke"}
)
check("POST approve returns 200", status == 200, str(status))
check("state becomes approved", approved.get("state") == "approved")
check(
    "protected items extracted on approval",
    len(approved.get("protected_items", [])) > 0,
    f"{len(approved.get('protected_items', []))} items",
)

status, batch = call(
    "POST",
    "/translations",
    {"message_id": message_id, "target_languages": ["es", "hi"], "locale": "es-US"},
)
check("POST /translations returns 200 after approval", status == 200, str(status))
check("two translations produced", len(batch.get("translations", [])) == 2)

status, one = call(
    "POST", "/translations", {"message_id": message_id, "target_languages": ["es"]}
)
check(
    "a single language is rejected (message already approved, so 400)",
    status == 400,
    str(status),
)

status, _ = call(
    "POST", "/translations", {"message_id": message_id, "target_languages": ["es", "zz"]}
)
check("an unsupported language is rejected", status == 400, str(status))

print("\n5. Verify")
translation_id = batch["translations"][0]["id"]
status, report = call("POST", "/verification", {"translation_id": translation_id})
check("POST /verification returns 200", status == 200, str(status))
check("fact map built", len(report.get("checks", [])) > 0, f"{len(report.get('checks', []))} checks")
check("human review is required", report.get("human_review_required") is True)
check(
    "overall status is a known value",
    report.get("overall_status") in {"PASS", "WARNING", "FAIL", "REVIEW", "ESCALATED"},
    str(report.get("overall_status")),
)
print("\n6. High-risk escalation")
status, risky = call(
    "POST",
    "/messages",
    {
        "source_message": (
            "Your child has been suspended for three school days. You have the right "
            "to appeal this decision."
        ),
        "audience": "families",
        "risk_level": "routine",
    },
)
risky_id = risky["id"]
call("POST", "/messages/rewrite", {"message_id": risky_id})
call("POST", f"/messages/{risky_id}/approve", {"approved": True, "reviewer": "smoke"})
_, risky_batch = call(
    "POST", "/translations", {"message_id": risky_id, "target_languages": ["es", "hi"]}
)
_, risky_report = call(
    "POST", "/verification", {"translation_id": risky_batch["translations"][0]["id"]}
)
check(
    "suspension escalates despite declared routine",
    risky_report.get("overall_status") == "ESCALATED",
    str(risky_report.get("overall_status")),
)
check(
    "escalation note is the required guidance",
    "Professional human translation" in (risky_report.get("escalation_note") or ""),
)
check("risk level is high", risky_report.get("risk", {}).get("level") == "high")

status, escalation = call(
    "POST",
    "/escalation/check",
    {"text": "There is an emergency evacuation at 3 p.m.", "declared_risk_level": None},
)
check("POST /escalation/check returns 200", status == 200, str(status))
check("emergency is high risk", escalation.get("level") == "high")
check("AI output is never final", escalation.get("ai_output_is_final") is False)

print("\n7. Error handling")
status, missing = call("GET", "/messages/00000000-0000-0000-0000-000000000000")
check("unknown message returns 404", status == 404, str(status))
check(
    "error uses the standard envelope",
    isinstance(missing, dict) and "error" in missing and "code" in missing["error"],
)
check("no stack trace is returned", "Traceback" not in json.dumps(missing))

status, _ = call("POST", "/messages", {"audience": "families"})
check("missing source returns 422", status == 422, str(status))

print("\n8. Delete")
status, _ = call("DELETE", f"/messages/{message_id}")
check("DELETE returns 204", status == 204, str(status))
status, _ = call("GET", f"/messages/{message_id}")
check("deleted message is gone", status == 404, str(status))

passed = sum(results)
total = len(results)
print("\n" + "=" * 62)
print(f"LIVE SMOKE TEST: {passed}/{total} checks passed")
print(f"FAILURES: {total - passed}")