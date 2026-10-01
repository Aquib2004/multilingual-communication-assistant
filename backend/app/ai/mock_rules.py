"""Rule-based plain-language rewriting, usable with no API key.

This is a curated phrase table drawn from plain-language references, not a
model. It handles the transformations that matter most for family
communication: named actors, direct verbs, explicit deadlines, and removal of
courtesy filler.

It exists so the whole pipeline can be run, demoed and tested offline. It does
not replace a real model for production use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RewriteRule:
    """One plain-language substitution.

    Attributes:
        pattern: What to find, matched case-insensitively.
        replacement: The clearer wording.
        reason: Why it is clearer, phrased for a parent to read.
        reason_code: Stable identifier used in the change summary.
    """

    pattern: re.Pattern[str]
    replacement: str
    reason: str
    reason_code: str


def _rule(pattern: str, replacement: str, reason: str, code: str) -> RewriteRule:
    """Compile one rewrite rule, case-insensitively."""
    return RewriteRule(
        pattern=re.compile(pattern, re.IGNORECASE),
        replacement=replacement,
        reason=reason,
        reason_code=code,
    )


#: Ordered. Earlier rules run first so a later rule cannot undo an earlier one.
REWRITE_RULES: tuple[RewriteRule, ...] = (
    # --- Courtesy filler that states no action ------------------------------
    _rule(
        r"\bYour cooperation is appreciated\.?",
        "",
        "'Your cooperation is appreciated' is a courtesy phrase that states no "
        "action. Removed so the real request stands on its own.",
        "remove_courtesy_filler",
    ),
    _rule(
        r"\bWe appreciate your cooperation\.?",
        "Thank you for your help.",
        "Replaced a formal courtesy phrase with a direct thank you.",
        "simplify_courtesy",
    ),
    # --- Formal or unfamiliar address ---------------------------------------
    _rule(
        r"\bContact the undersigned with inquiries\.?",
        "Questions? Contact the program office.",
        "'The undersigned' is unfamiliar. Named the response path instead.",
        "name_response_path",
    ),
    _rule(
        r"\bPlease do not hesitate to contact",
        "Please contact",
        "Removed a phrase that added length without adding meaning.",
        "remove_hesitation_phrase",
    ),
    _rule(
        r"\bShould you have any questions,? please",
        "If you have questions, please",
        "Replaced an indirect opening with a direct conditional.",
        "direct_conditional",
    ),
    # --- Passive constructions naming no actor -----------------------------
    _rule(
        r"\bStudents are expected to ([a-z]+)\b",
        r"Students should \1",
        "Named the actor and used a direct verb instead of 'are expected to'.",
        "name_the_actor",
    ),
    _rule(
        r"\bFamilies are asked to ([a-z]+)\b",
        r"Please \1",
        "Turned a passive request into a direct one.",
        "passive_to_imperative",
    ),
    _rule(
        r"\bIt is required that (families|students|parents) ([a-z]+)\b",
        r"\1 must \2",
        "Replaced a wordy construction with a direct requirement.",
        "simplify_requirement",
    ),
    _rule(
        r"\b(The form|Forms) (is|are) to be (returned|submitted|sent) (by|on|to)\b",
        r"Return \1 by",
        "Made the requested action explicit as an instruction.",
        "explicit_action",
    ),
    # --- Vague deadlines ----------------------------------------------------
    # --- Vague deadlines ----------------------------------------------------
    _rule(
        r"\bin a timely manner\.?",
        "by the date stated below.",
        "In a timely manner cannot be translated into a date. Replaced it with "
        "a reference to the actual date; add the date if it is missing.",
        "replace_vague_deadline",
    ),
    _rule(
        r"\bat your earliest convenience\.?",
        "as soon as you can.",
        "Replaced a formal phrase with plain wording.",
        "simplify_convenience",
    ),
    _rule(
        r"\breturn the form soon\.?",
        "return the form by [DEADLINE].",
        "Soon is not a usable deadline. Replaced it with a marked placeholder "
        "so a human must supply the real date before translating.",
        "replace_vague_deadline",
    ),
)

SHORTENING_RULES: tuple[RewriteRule, ...] = (
    _rule(
        r"\bin order to\b",
        "to",
        "Removed a phrase that added words, not meaning.",
        "shorten_phrase",
    ),
    _rule(
        r"\bprior to\b",
        "before",
        "'Prior to' is longer and less direct than 'before'.",
        "shorten_phrase",
    ),
    _rule(
        r"\bsubsequent to\b",
        "after",
        "'Subsequent to' is less direct than 'after'.",
        "shorten_phrase",
    ),
    _rule(
        r"\bwith regard to\b",
        "about",
        "Replaced a formal phrase with a plain one.",
        "shorten_phrase",
    ),
    _rule(
        r"\bat this point in time\b",
        "now",
        "Replaced a long phrase with one word.",
        "shorten_phrase",
    ),
    _rule(r"\bis able to\b", "can", "'Is able to' is longer than 'can'.", "shorten_phrase"),
    _rule(
        r"\bfor the purpose of\b", "to", "Replaced a long phrase with one word.", "shorten_phrase"
    ),
    _rule(
        r"\bthe month of\b",
        "",
        "Removed a phrase that added words without meaning.",
        "shorten_phrase",
    ),
    _rule(
        r"\bplease be advised that\b",
        "please note that",
        "Used plainer wording.",
        "simplify_phrase",
    ),
    _rule(r"\bkindly be advised\b", "please note", "Used plainer wording.", "simplify_phrase"),
    _rule(r"\bplease be advised\b", "please note", "Used plainer wording.", "simplify_phrase"),
    _rule(
        r"\bwill commence\b",
        "will start",
        "'Commence' is a formal word families rarely use.",
        "simplify_jargon",
    ),
    _rule(
        r"\bterminate the school day early\b",
        "end school early",
        "Replaced a formal phrase with plain wording.",
        "simplify_jargon",
    ),
    _rule(
        r"\bascertain\b", "find out", "Replaced a formal word with a plain one.", "simplify_jargon"
    ),
    _rule(r"\bpurchase\b", "buy", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\brequire\b", "need", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\badditional\b", "more", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\bnumerous\b", "many", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\bcommence\b", "start", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\bfacilitate\b", "help", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\bendeavor\b", "try", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\butilize\b", "use", "Replaced a formal word with a plain one.", "simplify_jargon"),
    _rule(r"\bterminate\b", "end", "Replaced a formal word with a plain one.", "simplify_jargon"),
)

#: Every rule, in application order.
ALL_REWRITE_RULES: tuple[RewriteRule, ...] = REWRITE_RULES + SHORTENING_RULES


def collapse_whitespace(text: str) -> str:
    """Tidy spacing and doubled punctuation left behind by substitutions."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"([.,;:])\1+", r"\1", text)
    text = re.sub(r"\s*,\s*,", ",", text)
    return text.strip()


def tidy_sentences(text: str) -> str:
    """Reassemble sentences after substitutions, dropping emptied ones."""
    parts = [collapse_whitespace(part) for part in re.split(r"(?<=\.)\s+", text)]
    return " ".join(part for part in parts if part)
