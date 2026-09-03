"""The legacy REAPER pattern registry, extracted without semantic changes."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class PatternDefinition:
    pattern_id: str
    weight: float
    terms: Tuple[str, ...]


PATTERNS: Tuple[PatternDefinition, ...] = (
    PatternDefinition("AUX_NEG", 3.0, ("cannot", "unable to", "won't", "doesn't")),
    PatternDefinition("VERB_FAIL", 2.8, ("crash", "fail", "break", "error")),
    PatternDefinition("WORKAROUND", 2.6, ("hack", "workaround", "manual fix", "temporary")),
    PatternDefinition("VERB_ADV", 2.5, ("forced to manually", "have to repeatedly")),
    PatternDefinition("TIME_WASTE", 2.3, ("takes too long", "very slow", "waste hours")),
    PatternDefinition("ADJ_DIFFICULTY", 2.0, ("difficult", "hard to", "confusing")),
    PatternDefinition("INTENT_HATE", 3.2, ("hate when", "infuriating", "nightmare")),
    PatternDefinition("WTP_EXPLICIT", 3.5, ("i'd pay", "worth every", "take my money", "budget for")),
    PatternDefinition("IMPACT_LOSS", 2.9, ("losing", "costing", "ruined", "lost customers")),
    PatternDefinition("NO_SOLUTION", 2.7, ("no one has solved", "why doesn", "still no good")),
    PatternDefinition("REPETITIVE", 2.4, ("every single time", "constantly have to")),
)

MONETIZATION_MULTIPLIERS = {
    "WTP_EXPLICIT": 2.0,
    "INTENT_HATE": 1.8,
    "IMPACT_LOSS": 1.7,
    "TIME_WASTE": 1.6,
    "WORKAROUND": 1.5,
    "AUX_NEG": 1.4,
    "NO_SOLUTION": 1.4,
    "VERB_FAIL": 1.3,
    "REPETITIVE": 1.3,
    "VERB_ADV": 1.2,
    "ADJ_DIFFICULTY": 1.1,
}
