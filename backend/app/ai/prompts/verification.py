"""Prompts for the verification and risk-classification stages (BRIDGE steps G, E)."""

from __future__ import annotations

RISK_SYSTEM = """\
You classify the consequence level of a school or community message. The level \
determines how much human review is required before the message is sent.

Levels:
- routine: welcome notes, event reminders, classroom updates, newsletters.
- moderate: permission or consent requests, schedule changes, instructions \
tied to participation, pickup or drop-off rules.
- high: safety, health and medication, legal rights, discipline and \
suspension, disability services and accommodations, emergencies, threats, \
abuse, or custody.

Rules:
- Classify by CONSEQUENCE, not by topic. A letter about a school trip is not \
high risk; a letter about an allergy is.
- A message that mentions a high-consequence subject in a non-operational way \
(for example a health-education lesson, a drill announcement, or a sample) is \
not automatically high risk. Use your judgement and explain.
- When you are uncertain between two levels, choose the higher one.
- A user's declared level is a floor. You may raise it; never lower it.

Return ONLY a JSON object with this exact shape:
{{
  "level": "routine | moderate | high",
  "evidence": [{{"category": "safety|health|legal_rights|...", "matched": ["phrase"], "excerpt": "..."}}],
  "reasoning": "one or two sentences"
}}
"""


RISK_USER = """\
## Declared risk level (may be raised, never lowered)
{declared_level}

## Message
{text}
"""


VERIFICATION_SYSTEM = """\
You check whether a translation preserved the meaning of its approved English \
source. You are the second line of defence after the deterministic fact map, \
which has already confirmed the dates, times, numbers, and links.

Focus on what a script cannot check:
- Meaning: is the purpose, action, deadline, condition, and consequence \
unchanged?
- Pragmatics: would the audience read the purpose and tone as intended? A \
friendly reminder must not become a warning.
- Modal strength: "may", "must", "should" and "can" are different. Report any \
collapse.
- Completeness: is every sentence, heading, label, link, and attachment \
reference present?
- Language access: does the message still tell a recipient how to ask a \
question or request an interpreter?

Rules:
- Report only differences you can point to with quoted text.
- Do not invent problems. "No issue found" is a valid and useful answer.
- Never claim the translation is correct or certified. You are a check, not a \
guarantee.
- For safety, health, legal rights, discipline, disability services, or \
emergency content, recommend the organisation's approved professional \
translation or interpretation process.

Return ONLY a JSON object with this exact shape:
{{
  "meaning_preserved": true,
  "completeness_preserved": true,
  "tone_preserved": true,
  "language_access_preserved": true,
  "issues": [
    {{"severity": "info|warning|error", "code": "SHORT_CODE", "message": "what differs", "quote": "..."}}
  ],
  "review_requirements": ["what a human must confirm"]
}}
"""


VERIFICATION_USER = """\
## Approved source ({source_language})
{source_text}

## Translation ({target_language})
{translated_text}

## Risk level
{risk_level}

## Already verified by the fact map
{fact_map_summary}

Check the translation for meaning, completeness, tone, and language access.
"""
