"""API-level tests over the real FastAPI app.

The in-process client here still goes through routing, dependency injection,
Pydantic validation, and serialisation. The defects pinned in this file were
originally found by the live HTTP smoke test (``smoke_live.py``) rather than by
unit tests, because they only appear once a model is serialised or reloaded
from the database.
"""

from __future__ import annotations

from httpx import AsyncClient

SOURCE = (
    "Students are expected to return the field trip permission form in a timely manner. "
    "The form should be signed by a parent and returned to your child's teacher by "
    "Friday, September 18. Contact the undersigned with inquiries. Your cooperation "
    "is appreciated."
)

RISKY_SOURCE = (
    "Your child has been suspended for three school days. You have the right to appeal "
    "this decision."
)


class TestHealth:
    """The health endpoint must stay cheap and always answer."""

    async def test_health_reports_provider_and_database(self, client: AsyncClient) -> None:
        response = await client.get("/api/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["ai_provider"] == "mock"
        assert body["database"] == "connected"

    async def test_request_id_header_is_present(self, client: AsyncClient) -> None:
        response = await client.get("/api/health")
        assert "X-Request-ID" in response.headers


class TestReferenceData:
    """Reference endpoints the UI depends on."""

    async def test_languages_lists_registered_targets(self, client: AsyncClient) -> None:
        response = await client.get("/api/languages")

        assert response.status_code == 200
        codes = [item["code"] for item in response.json()["targets"]]
        assert set(codes) >= {"es", "hi", "ur"}

    async def test_risk_levels_lists_three_tiers(self, client: AsyncClient) -> None:
        response = await client.get("/api/risk-levels")

        assert response.status_code == 200
        levels = [item["level"] for item in response.json()["levels"]]
        assert levels == ["routine", "moderate", "high"]

    async def test_examples_are_deidentified(self, client: AsyncClient) -> None:
        response = await client.get("/api/examples")

        assert response.status_code == 200
        for item in response.json()["items"]:
            assert "mramirez" not in item["source_message"].lower()


class TestMessageLifecycle:
    """Create, rewrite, approve."""

    async def test_create_returns_201_and_draft(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/messages", json={"source_message": SOURCE, "audience": "families"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["state"] == "draft"
        assert body["approved_message"] is None

    async def test_create_rejects_a_blank_source(self, client: AsyncClient) -> None:
        response = await client.post("/api/messages", json={"source_message": "   "})
        assert response.status_code == 422

    async def test_rewrite_returns_changes_and_questions(self, client: AsyncClient) -> None:
        """Regression: the response model rejected RewriteChanges objects.

        Passing the AI-layer model straight into the Pydantic response model
        raised a ValidationError and surfaced to the user as a 500.
        """
        response = await client.post("/api/messages/rewrite", json={"source_message": SOURCE})

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["rewritten_message"]
        for change in body["changes"]:
            assert set(change) >= {"original", "revised", "reason"}

    async def test_rewrite_surfaces_vague_deadlines(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/messages/rewrite", json={"source_message": "Return the form soon."}
        )

        assert response.status_code == 200
        assert response.json()["open_questions"]

    async def test_approve_frozen_text_and_protected_items(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]

        await client.post("/api/messages/rewrite", json={"message_id": message_id})
        response = await client.post(f"/api/messages/{message_id}/approve", json={"approved": True})

        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "approved"
        assert body["approved_message"]
        assert body["protected_items"], "approval must extract protected items"


class TestApprovalGate:
    """The gate is the product's central guarantee."""

    async def test_translation_refused_before_approval(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]

        response = await client.post(
            "/api/translations",
            json={"message_id": message_id, "target_languages": ["es", "hi"]},
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SOURCE_NOT_APPROVED"

    async def test_translation_allowed_after_approval(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]
        await client.post("/api/messages/rewrite", json={"message_id": message_id})
        await client.post(f"/api/messages/{message_id}/approve", json={"approved": True})

        response = await client.post(
            "/api/translations",
            json={"message_id": message_id, "target_languages": ["es", "hi"]},
        )

        assert response.status_code == 200
        assert len(response.json()["translations"]) == 2

    async def test_approval_is_sticky_after_translation(self, client: AsyncClient) -> None:
        """Regression: translating used to revoke approval.

        Translating moved the state to ``translated`` and the gate then refused
        every later call, so adding a third language or verifying a second
        translation was impossible.
        """
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]
        await client.post("/api/messages/rewrite", json={"message_id": message_id})
        await client.post(f"/api/messages/{message_id}/approve", json={"approved": True})
        await client.post(
            "/api/translations",
            json={"message_id": message_id, "target_languages": ["es", "hi"]},
        )

        response = await client.post(
            "/api/translations",
            json={"message_id": message_id, "target_languages": ["es", "hi", "ur"]},
        )

        assert response.status_code == 200, response.text

    async def test_reject_returns_to_draft(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]
        await client.post("/api/messages/rewrite", json={"message_id": message_id})

        response = await client.post(
            f"/api/messages/{message_id}/reject",
            json={"notes": "Use the family-facing term instead."},
        )

        assert response.status_code == 200
        assert response.json()["state"] == "draft"

    async def test_reject_requires_notes(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]

        response = await client.post(f"/api/messages/{message_id}/reject", json={"notes": ""})
        assert response.status_code == 422


class TestTranslationErrors:
    """Invalid translation requests are refused with a useful code."""

    async def test_fewer_than_two_languages_is_rejected(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]
        await client.post("/api/messages/rewrite", json={"message_id": message_id})
        await client.post(f"/api/messages/{message_id}/approve", json={"approved": True})

        response = await client.post(
            "/api/translations",
            json={"message_id": message_id, "target_languages": ["es"]},
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "MINIMUM_TWO_LANGUAGES"

    async def test_unsupported_language_is_rejected(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]
        await client.post("/api/messages/rewrite", json={"message_id": message_id})
        await client.post(f"/api/messages/{message_id}/approve", json={"approved": True})

        response = await client.post(
            "/api/translations",
            json={"message_id": message_id, "target_languages": ["es", "zz"]},
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "UNSUPPORTED_LANGUAGE"


class TestVerificationAndEscalation:
    """Verification and the high-consequence routing."""

    async def test_verification_builds_a_fact_map(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]
        await client.post("/api/messages/rewrite", json={"message_id": message_id})
        await client.post(f"/api/messages/{message_id}/approve", json={"approved": True})
        batch = await client.post(
            "/api/translations",
            json={"message_id": message_id, "target_languages": ["es", "hi"]},
        )
        translation_id = batch.json()["translations"][0]["id"]

        response = await client.post("/api/verification", json={"translation_id": translation_id})

        assert response.status_code == 200
        body = response.json()
        assert body["checks"]
        assert body["human_review_required"] is True
        assert body["overall_status"] in {"PASS", "WARNING", "FAIL", "REVIEW", "ESCALATED"}

    async def test_escalation_check_reports_high_risk(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/escalation/check",
            json={"text": "There is an emergency evacuation at 3 p.m."},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["level"] == "high"
        assert body["ai_output_is_final"] is False
        assert "Professional human translation" in body["escalation_note"]

    async def test_escalation_ignores_a_downgrade(self, client: AsyncClient) -> None:
        """A declared 'routine' level must not suppress a high-risk detection."""
        response = await client.post(
            "/api/escalation/check",
            json={"text": RISKY_SOURCE, "declared_risk_level": "routine"},
        )

        assert response.status_code == 200
        assert response.json()["level"] == "high"

    async def test_routine_message_is_not_escalated(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/escalation/check",
            json={"text": "Our book fair is on November 14. Please RSVP by November 6."},
        )

        assert response.status_code == 200
        assert response.json()["level"] in {"routine", "moderate"}


class TestErrorHandling:
    """Errors must be safe, structured, and free of internals."""

    async def test_unknown_message_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/api/messages/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MESSAGE_NOT_FOUND"
        assert "Traceback" not in response.text

    async def test_unknown_translation_returns_404(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/verification", json={"translation_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert response.status_code == 404

    async def test_malformed_body_returns_422_envelope(self, client: AsyncClient) -> None:
        response = await client.post("/api/messages", json={"audience": "families"})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_delete_removes_the_workspace(self, client: AsyncClient) -> None:
        created = await client.post("/api/messages", json={"source_message": SOURCE})
        message_id = created.json()["id"]

        deleted = await client.delete(f"/api/messages/{message_id}")
        assert deleted.status_code == 204

        fetched = await client.get(f"/api/messages/{message_id}")
        assert fetched.status_code == 404
