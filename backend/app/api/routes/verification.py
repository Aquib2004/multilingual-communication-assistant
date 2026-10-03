"""Verification and escalation routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import (
    MessageServiceDep,
    SessionDep,
    VerificationServiceDep,
)
from app.api.routes.messages import _report_to_response
from app.core.errors import TranslationNotFoundError
from app.models.translation import Translation
from app.schemas.verification import (
    EscalationRequest,
    EscalationResponse,
    RiskEvidenceResponse,
    VerificationReportResponse,
    VerificationRequest,
)
from app.services.escalation_service import EscalationService

router = APIRouter(tags=["verification"])


@router.post(
    "/verification",
    response_model=VerificationReportResponse,
    summary="Generate a verification report for a translation",
)
async def create_verification(
    payload: VerificationRequest,
    session: SessionDep,
    service: VerificationServiceDep,
) -> VerificationReportResponse:
    """Run every verification layer and persist the report.

    The report is the durable artefact: what was checked, what failed, and what
    still needs a fluent human reviewer.
    """
    row = await session.get(Translation, payload.translation_id)
    if row is None:
        raise TranslationNotFoundError

    report = await service.verify(session, row)
    await session.commit()
    await session.refresh(report)
    return _report_to_response(report)


@router.get(
    "/verification/{report_id}",
    response_model=VerificationReportResponse,
    summary="Fetch a verification report",
)
async def get_verification(
    report_id: UUID, session: SessionDep, service: VerificationServiceDep
) -> VerificationReportResponse:
    """Return a previously generated report."""
    report = await service.get(session, str(report_id))
    return _report_to_response(report)


@router.post(
    "/escalation/check",
    response_model=EscalationResponse,
    summary="Classify risk and return escalation guidance",
)
async def check_escalation(payload: EscalationRequest) -> EscalationResponse:
    """Decide whether a message needs professional human translation.

    A declared risk level acts as a floor: declaring a suspension letter
    "routine" still returns ``high``. For high-consequence content the response
    always carries the escalation note and sets ``ai_output_is_final`` to false.
    """
    assessment = EscalationService().assess(
        payload.text, payload.declared_risk_level.value if payload.declared_risk_level else None
    )
    return EscalationResponse(
        level=assessment.level.value,
        declared_by_user=assessment.declared_by_user,
        # RiskEvidence is a dataclass; convert it rather than passing it through.
        evidence=[RiskEvidenceResponse(**item.to_dict()) for item in assessment.evidence],
        escalation_note=assessment.escalation_note,
        review_requirements=assessment.review_requirements,
        ai_output_is_final=False,
    )


__all__ = ["MessageServiceDep", "router"]
