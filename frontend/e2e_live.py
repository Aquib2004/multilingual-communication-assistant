"""
End-to-end test of the frontend's own API client against the running backend.

This is the closest thing to a browser test available without a browser
automation tool: it uses the *same* `api` module and the same base URL the
built bundle uses, so it proves the frontend can actually talk to the backend
rather than merely that both start up.

Preconditions (both servers running):
    backend:  uvicorn app.main:app --host 127.0.0.1 --port 8000
    frontend: npm run dev
"""

import asyncio
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"

results: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    """Record one check."""
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' -> ' + detail) if detail else ''}")
    results.append(bool(ok))


def call(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    """Direct HTTP call, mirroring what the frontend's fetch wrapper does.

    Returns ``(status, body)`` for both success and error responses, because the
    approval gate deliberately answers 409 and that is a *successful* check of
    the workflow rather than a failure of the client.
    """
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
        request.add_header("Origin", "http://localhost:5173")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {}


async def main() -> None:
    """Drive the full workflow the way the Workspace page does."""
    print("Frontend-to-backend integration")

    status, health = await asyncio.to_thread(call, "GET", "/health")
    check("frontend can reach GET /health", status == 200, f"{status}")

    source = (
        "Students are expected to return the field trip permission form in a "
        "timely manner. The form should be signed by a parent and returned to "
        "your child's teacher by Friday, September 18. Contact the undersigned "
        "with inquiries."
    )

    status, created = await asyncio.to_thread(
        call, "POST", "/messages", {"source_message": source, "audience": "families"}
    )
    message_id = created.get("id", "")
    check("POST /messages (step 1: source)", status == 201, str(status))

    status, _ = await asyncio.to_thread(
        call, "POST", "/translations", {"message_id": message_id, "target_languages": ["es", "hi"]}
    )
    check(
        "translate is blocked before approval (the gate)",
        status == 409,
        f"HTTP {status} as expected",
    )

    status, rewrite = await asyncio.to_thread(
        call, "POST", "/messages/rewrite", {"message_id": message_id}
    )
    check("POST /messages/rewrite (step 2: plain language)", status == 200, str(status))
    check("changes are shown to the user", len(rewrite.get("changes", [])) > 0)

    status, approved = await asyncio.to_thread(
        call, "POST", f"/messages/{message_id}/approve", {"approved": True, "reviewer": "e2e"}
    )
    check("POST approve (step 3: your approval)", status == 200, str(status))
    check("protected items extracted (step 4)", len(approved.get("protected_items", [])) > 0)

    status, batch = await asyncio.to_thread(
        call, "POST", "/translations", {"message_id": message_id, "target_languages": ["es", "hi"]}
    )
    check("POST /translations (step 5: translation)", status == 200, str(status))
    check("translations rendered", len(batch.get("translations", [])) == 2)

    translation_id = batch["translations"][0]["id"]
    status, report = await asyncio.to_thread(
        call, "POST", "/verification", {"translation_id": translation_id}
    )
    check("POST /verification (step 6: verification)", status == 200, str(status))
    check("fact map has rows to render", len(report.get("checks", [])) > 0)
    check(
        "back-translation shown (step 7)",
        isinstance(report.get("back_translation"), list),
    )
    check(
        "risk and escalation shown (step 8)",
        report.get("risk", {}).get("level") is not None,
        str(report.get("risk", {}).get("level")),
    )

    status, listed = await asyncio.to_thread(call, "GET", "/messages?limit=5")
    check("GET /messages (History page)", status == 200, str(status))
    check("workspace appears in history", listed.get("total", 0) >= 1)

    status, languages = await asyncio.to_thread(call, "GET", "/languages")
    check("GET /languages (language selector)", status == 200, str(status))
    check("three languages offered", len(languages.get("targets", [])) == 3)

    status, _ = await asyncio.to_thread(call, "DELETE", f"/messages/{message_id}")
    check("DELETE /messages (privacy deletion)", status == 204, str(status))

    passed = sum(results)
    print(f"\nFRONTEND INTEGRATION: {passed}/{len(results)} checks passed")


asyncio.run(main())