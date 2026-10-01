"""Health, language, risk-level, and demo-example endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.ai.factory import get_provider
from app.api.dependencies import SettingsDep
from app.core.languages import LOCALES, SOURCE_LANGUAGE, list_languages
from app.db.base import utc_now
from app.db.database import database_is_ready
from app.schemas.verification import (
    ExampleMessageResponse,
    ExamplesResponse,
    HealthResponse,
    LanguageInfo,
    LanguagesResponse,
    RiskLevelInfo,
    RiskLevelsResponse,
)
from app.verification.risk_classifier import RISK_LEVELS, RiskTier

router = APIRouter(tags=["reference"])

#: Repository root, used to load the bundled fictional demo examples.
EXAMPLES_ROOT = Path(__file__).resolve().parents[4] / "examples"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health, including the active AI provider",
)
async def health(settings: SettingsDep) -> HealthResponse:
    """Report liveness, database connectivity, and the configured provider.

    Always returns 200 with a ``status`` of ``ok`` or ``degraded`` so an
    orchestrator can distinguish "reachable but impaired" from "down".
    """
    provider = get_provider()
    database_ok = await database_is_ready()

    return HealthResponse(
        status="ok" if database_ok else "degraded",
        app=settings.app_name,
        version=settings.version,
        environment=settings.app_env,
        ai_provider=provider.name,
        database="connected" if database_ok else "unavailable",
        timestamp=utc_now(),
        details={
            "ai_model": provider.model,
            "ai_provider_healthy": await provider.health(),
            "database_dialect": "sqlite" if settings.is_sqlite else "postgresql",
            "log_message_content": settings.should_log_message_content,
        },
    )


@router.get(
    "/languages",
    response_model=LanguagesResponse,
    summary="Supported source and target languages",
)
async def languages() -> LanguagesResponse:
    """List the source language and every registered translation target."""
    return LanguagesResponse(
        source=LanguageInfo(**SOURCE_LANGUAGE.to_dict()),
        targets=[LanguageInfo(**lang.to_dict()) for lang in list_languages()],
        locales=[locale.tag for locale in LOCALES],
    )


@router.get(
    "/risk-levels",
    response_model=RiskLevelsResponse,
    summary="Risk levels and the review each requires",
)
async def risk_levels() -> RiskLevelsResponse:
    """List the three risk tiers with their examples and review requirements."""
    return RiskLevelsResponse(
        levels=[
            RiskLevelInfo(
                level=RiskTier(tier),
                label=str(info["label"]),
                description=str(info["description"]),
                examples=[str(item) for item in info["examples"]],
                review_requirements=[str(item) for item in info["review_requirements"]],
            )
            for tier, info in RISK_LEVELS.items()
        ]
    )


@router.get(
    "/examples",
    response_model=ExamplesResponse,
    summary="Bundled fictional demo messages",
)
async def examples() -> ExamplesResponse:
    """Load the fictional, de-identified demo messages shipped in ``examples/``.

    Nothing here is real data. If the directory is missing from a packaged
    install, an empty list is returned rather than raising.
    """
    items: list[ExampleMessageResponse] = []

    for path in sorted(EXAMPLES_ROOT.rglob("*.json")) if EXAMPLES_ROOT.exists() else []:
        try:
            payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "source_message" not in payload:
            continue

        items.append(
            ExampleMessageResponse(
                id=str(payload.get("id", path.stem)),
                title=str(payload.get("title", path.stem)),
                risk_level=payload.get("risk_level", "routine"),
                category=path.parent.name,
                target_languages=payload.get("target_languages", []),
                locale=payload.get("locale", "en-US"),
                tone=payload.get("tone", ""),
                audience=payload.get("audience", ""),
                purpose=payload.get("purpose", ""),
                action=payload.get("action", ""),
                deadline=payload.get("deadline", ""),
                source_message=payload["source_message"],
            )
        )

    return ExamplesResponse(items=items, total=len(items))
