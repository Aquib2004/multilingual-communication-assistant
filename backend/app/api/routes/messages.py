"""Message routes: the Communication Workspace and the approval gate."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import MessageServiceDep, SessionDep
from app.core.errors import ValidationError
from app.core.languages import get_language
from app.models.message import Message, MessageState, RiskLevel
from app.schemas.common import (
    MessageStateEnum,
    PIIFindingSchema,
    ProtectedItemTypeEnum,
    ReadingLevelSchema,
    RiskLevelEnum,
    VerificationStatusEnum,
)
from app.schemas.message import (
    ApproveRequest,
    ChangeSummary,
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
    ProtectedItemResponse,
    RejectRequest,
    RewriteRequest,
    RewriteResponse,
)
from app.schemas.translation import TranslationResponse
from app.schemas.verification import (
    RiskResponse,
    ToneAssessmentResponse,
    VerificationReportResponse,
    VerificationSummaryResponse,
)

router = APIRouter(prefix="/messages", tags=["messages"])


def to_response(message: Message) -> MessageResponse:
    """Convert an ORM workspace into its API representation.

    Kept as a free function so every route serialises identically and there is
    exactly one place that knows the ORM-to-schema mapping.
    """
    return MessageResponse(
        id=message.id,
        state=MessageStateEnum(message.state.value),
        audience=message.audience,
        purpose=message.purpose,
        action=message.action,
        deadline=message.deadline,
        contact_path=message.contact_path,
        tone=message.tone,
        locale=message.locale,
        risk_level=RiskLevelEnum(message.risk_level.value),
        source_message=message.source_message,
        revised_message=message.revised_message,
        changes=message.changes or [],
        open_questions=message.open_questions or [],
        reading_level=message.reading_level,
        approved_message=message.approved_message,
        approved_at=message.approved_at,
        approved_by=message.approved_by,
        reviewer_feedback=message.reviewer_feedback,
        target_languages=message.target_languages or [],
        pii_warnings=message.pii_warnings or [],
        protected_items=[
            ProtectedItemResponse(
                id=item.id,
                item_type=ProtectedItemTypeEnum(item.item_type.value),
                value=item.value,
                placeholder=item.placeholder,
                must_match_exactly=item.must_match_exactly,
                start_offset=item.start_offset,
                end_offset=item.end_offset,
                context_sentence=item.context_sentence,
                source=item.source,
            )
            for item in message.protected_items
        ],
        translations=[
            TranslationResponse(
                id=row.id,
                message_id=row.message_id,
                target_language=row.target_language,
                language_name=_language_name(row.target_language),
                locale=row.locale,
                translated_message=row.translated_message,
                back_translation=row.back_translation,
                placeholders=row.placeholders or {},
                protected_items=row.protected_items or [],
                uncertainties=row.uncertainties or [],
                terminology_notes=row.terminology_notes or [],
                provider=row.provider,
                model=row.model,
                created_at=row.created_at,
            )
            for row in message.translations
        ],
        verification_reports=[
            _report_to_response(report) for report in message.verification_reports
        ],
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _language_name(code: str) -> str:
    """Best-effort display name for a language code."""
    try:
        return get_language(code).name
    except Exception:
        return code


def _report_to_response(report: Any) -> VerificationReportResponse:
    """Convert a verification report ORM object into its API representation."""
    tone = report.tone
    return VerificationReportResponse(
        id=report.id,
        message_id=report.message_id,
        translation_id=report.translation_id,
        target_language=report.target_language,
        overall_status=VerificationStatusEnum(report.overall_status),
        human_review_required=report.human_review_required,
        summary=VerificationSummaryResponse(**_summary_counts(report.summary or {})),
        checks=[check.to_dict() for check in report.checks],
        back_translation=[pair.to_dict() for pair in report.back_translation_pairs],
        tone_assessment=_tone_assessment(tone),
        issues=[issue.to_dict() for issue in report.issues],
        risk=RiskResponse(
            level=RiskLevelEnum(report.risk_level),
            declared_by_user=(
                RiskLevelEnum(report.risk_declared_by_user)
                if report.risk_declared_by_user
                else None
            ),
            evidence=list(report.risk_evidence or []),
            review_requirements=list(report.review_requirements or []),
        ),
        escalation_note=report.escalation_note,
        review_requirements=list(report.review_requirements or []),
        provider=report.provider,
        model=report.model,
        verified_at=report.verified_at,
        created_at=report.created_at,
    )


def _summary_counts(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise the stored summary into the fixed response shape."""
    return {
        "total": int(raw.get("total", 0)),
        "passed": int(raw.get("passed", 0)),
        "warnings": int(raw.get("warnings", 0)),
        "failures": int(raw.get("failures", 0)),
        "review_required": int(raw.get("review_required", 0)),
    }


def _tone_assessment(tone: Any) -> ToneAssessmentResponse:
    """Build the tone response, tolerating a report saved without one.

    `ToneAssessmentResponse.tone` is required, so the empty case has to supply
    an explicit "unknown" rather than relying on model defaults.
    """
    if tone is None:
        return ToneAssessmentResponse(
            tone="unknown",
            mechanical_phrases=[],
            cultural_awkwardness=[],
            terminology_notes=[],
            status=VerificationStatusEnum.REVIEW_REQUIRED,
        )
    return ToneAssessmentResponse.model_validate(tone.to_dict())


def _reading_level_payload(raw: dict[str, Any]) -> ReadingLevelSchema:
    """Build the reading-level response, tolerating a provider's extra keys."""
    return ReadingLevelSchema.model_validate(raw or {})


# --- Routes -----------------------------------------------------------------


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a communication workspace",
)
async def create_message(
    payload: MessageCreateRequest,
    session: SessionDep,
    service: MessageServiceDep,
) -> MessageResponse:
    """Create a workspace from a source message and the BRIDGE context.

    The message starts in state ``draft``. It cannot be translated until it has
    been rewritten and approved.
    """
    message = await service.create(
        session,
        source_message=payload.source_message,
        audience=payload.audience,
        purpose=payload.purpose,
        action=payload.action,
        deadline=payload.deadline,
        contact_path=payload.contact_path,
        tone=payload.tone,
        risk_level=RiskLevel(payload.risk_level.value),
        target_languages=payload.target_languages,
        locale=payload.locale,
        protected_items=payload.protected_items,
    )
    await session.commit()
    await session.refresh(message)
    return to_response(message)


@router.get("", response_model=MessageListResponse, summary="List recent workspaces")
async def list_messages(
    session: SessionDep,
    service: MessageServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    state_filter: MessageState | None = Query(default=None, alias="state"),
    risk_level: RiskLevel | None = None,
) -> MessageListResponse:
    """Return a page of workspaces, newest first."""
    items, total = await service.list_recent(
        session, limit=limit, offset=offset, state=state_filter, risk_level=risk_level
    )
    return MessageListResponse(
        items=[to_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{message_id}", response_model=MessageResponse, summary="Get a workspace")
async def get_message(
    message_id: UUID, session: SessionDep, service: MessageServiceDep
) -> MessageResponse:
    """Return one workspace with every stage, translation, and report."""
    message = await service.get(session, message_id)
    return to_response(message)


@router.post(
    "/rewrite",
    response_model=RewriteResponse,
    summary="Rewrite a message in plain language",
)
async def rewrite_message(
    payload: RewriteRequest,
    session: SessionDep,
    service: MessageServiceDep,
) -> RewriteResponse:
    """Run the plain-language engine.

    Pass ``message_id`` to revise a saved workspace, or ``source_message`` for a
    one-off rewrite. Nothing is translated here: the result must be approved
    before that can happen.
    """
    existing: str | None = None
    message = None
    if payload.message_id:
        message = await service.get(session, payload.message_id)
        existing = message.source_message

    try:
        text = payload.resolved_text(existing)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    output, findings, provider, model = await service.rewrite(
        session,
        source_message=text,
        audience=message.audience if message else "",
        purpose=message.purpose if message else "",
        action=message.action if message else "",
        deadline=message.deadline if message else "",
        contact_path=message.contact_path if message else "",
        tone=message.tone if message else "warm, respectful, direct",
        risk_level=message.risk_level if message else RiskLevel.ROUTINE,
    )

    if message is not None:
        await service.apply_revision(session, message, output, findings)
        await session.commit()
        await session.refresh(message)

    return RewriteResponse(
        message_id=message.id if message else None,
        rewritten_message=output.rewritten_message,
        # Convert the AI-layer models to the API models explicitly. Passing
        # RewriteChanges straight through fails because the response model
        # forbids extra keys and expects its own ChangeSummary type.
        changes=[
            ChangeSummary(
                original=change.original,
                revised=change.revised,
                reason=change.reason,
            )
            for change in output.changes
        ],
        open_questions=list(output.open_questions),
        reading_level=_reading_level_payload(output.reading_level),
        pii_warnings=[
            PIIFindingSchema(
                category=finding.category,
                excerpt=finding.excerpt,
                severity=finding.severity,
            )
            for finding in findings
        ],
        provider=provider,
        model=model,
    )


@router.post(
    "/{message_id}/approve",
    response_model=MessageResponse,
    summary="Approve the revised source (the approval gate)",
)
async def approve_message(
    message_id: UUID,
    payload: ApproveRequest,
    session: SessionDep,
    service: MessageServiceDep,
) -> MessageResponse:
    """Approve a revision so it may be translated.

    This is the gate. Until it is called, ``POST /api/translations`` refuses the
    request with ``409 SOURCE_NOT_APPROVED``.
    """
    message = await service.get(session, message_id)

    if payload.approved:
        await service.approve(session, message, reviewer=payload.reviewer, notes=payload.notes)
    else:
        await service.reject(
            session, message, notes=payload.notes or "Revision rejected without notes."
        )

    await session.commit()
    await session.refresh(message)
    return to_response(message)


@router.post(
    "/{message_id}/reject",
    response_model=MessageResponse,
    summary="Send a revision back for another pass",
)
async def reject_message(
    message_id: UUID,
    payload: RejectRequest,
    session: SessionDep,
    service: MessageServiceDep,
) -> MessageResponse:
    """Return the workspace to ``draft`` with the reviewer's feedback."""
    message = await service.get(session, message_id)
    await service.reject(session, message, notes=payload.notes)
    await session.commit()
    await session.refresh(message)
    return to_response(message)


@router.get(
    "/{message_id}/protected-items",
    response_model=list[ProtectedItemResponse],
    summary="List the protected items found in the approved source",
)
async def protected_items(
    message_id: UUID, session: SessionDep, service: MessageServiceDep
) -> list[ProtectedItemResponse]:
    """Return the fact-map candidates with the placeholder each was given."""
    message = await service.get(session, message_id)
    return to_response(message).protected_items


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace and everything derived from it",
)
async def delete_message(
    message_id: UUID, session: SessionDep, service: MessageServiceDep
) -> Response:
    """Delete the workspace, its translations, and its verification reports."""
    message = await service.get(session, message_id)
    await service.delete(session, message)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
