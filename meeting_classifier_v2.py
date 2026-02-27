"""
Meeting Classification Module v2.0
Heuristically classifies meetings as refinement (stories) vs general (action items)
before sending to LLM for structured extraction.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Literal
import re

MeetingType = Literal["refinement", "general", "mixed", "unknown"]


@dataclass
class MeetingClassification:
    meeting_type: MeetingType
    refinement_score: float
    action_score: float
    title_hits: List[str]
    refinement_hits: List[str]
    action_hits: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


# --- Keyword lists (tune these for your teams) -------------------------------

REFINEMENT_TITLE_KEYWORDS = [
    "refinement",
    "backlog grooming",
    "grooming",
    "story workshop",
    "story refinement",
    "sprint planning",
    "planning poker",
    "estimation",
]

REFINEMENT_BODY_KEYWORDS = [
    "story point",
    "story points",
    "sp ",
    "estimate this",
    "estimate it",
    "acceptance criteria",
    "given when then",
    "given/when/then",
    "backlog item",
    "refine this",
    "split this story",
    "split the story",
    "create a story",
    "create a user story",
    "epic",
    "feature ticket",
    "technical spike",
    "sprint backlog",
    "product backlog",
    "groom the backlog",
    "definition of ready",
    "definition of done",
]

ACTION_BODY_KEYWORDS = [
    "next step",
    "next steps",
    "action item",
    "action items",
    "follow up",
    "follow-up",
    "take this away",
    "take an action",
    "can you send",
    "can you share",
    "please send",
    "please share",
    "schedule a meeting",
    "set up a meeting",
    "set up a call",
    "reach out to",
    "ping",
    "email them",
    "by when",
    "due date",
    "deadline",
    "owner",
    "who will own",
    "assign this",
    "we need to decide",
    "decision",
]


# --- Core functions ---------------------------------------------------------

def _find_matches(text: str, phrases: List[str]) -> List[str]:
    """
    Return list of phrases that appear in the text (case-insensitive).
    """
    hits = []
    lower = text.lower()
    for phrase in phrases:
        if phrase.lower() in lower:
            hits.append(phrase)
    return hits


def _score_matches(text: str, phrases: List[str], weight: float = 1.0) -> float:
    """
    Very simple scoring: count occurrences * weight.
    You can replace this with something more sophisticated if needed.
    """
    score = 0.0
    lower = text.lower()
    for phrase in phrases:
        # count non-overlapping occurrences
        count = len(re.findall(re.escape(phrase.lower()), lower))
        score += count * weight
    return score


def classify_meeting(
    title: str,
    transcript: str,
    refinement_title_weight: float = 2.0,
    refinement_body_weight: float = 1.0,
    action_body_weight: float = 1.0,
    min_conf_threshold: float = 1.5,
    dominance_factor: float = 1.3,
) -> MeetingClassification:
    """
    Heuristically classify a meeting as refinement, general, mixed, or unknown.

    - title is weighted more heavily than body text for refinement signals.
    - min_conf_threshold: minimum score to confidently call it refinement/general.
    - dominance_factor: how much higher one score must be than the other
      to be considered dominant (e.g. 1.3 = 30% higher).

    You can tweak thresholds to match your org's language.

    Returns a MeetingClassification dataclass.
    """

    title = title or ""
    transcript = transcript or ""

    combined_text = transcript  # you can also include title if you want

    # Title-based refinement hints
    title_hits = _find_matches(title, REFINEMENT_TITLE_KEYWORDS)
    title_score = _score_matches(title, REFINEMENT_TITLE_KEYWORDS,
                                 weight=refinement_title_weight)

    # Body-based refinement and action hints
    refinement_hits = _find_matches(combined_text, REFINEMENT_BODY_KEYWORDS)
    refinement_body_score = _score_matches(
        combined_text, REFINEMENT_BODY_KEYWORDS, weight=refinement_body_weight
    )

    action_hits = _find_matches(combined_text, ACTION_BODY_KEYWORDS)
    action_body_score = _score_matches(
        combined_text, ACTION_BODY_KEYWORDS, weight=action_body_weight
    )

    refinement_score = title_score + refinement_body_score
    action_score = action_body_score

    # --- Decide meeting type -----------------------------------------------

    meeting_type: MeetingType = "unknown"

    if refinement_score < 0.1 and action_score < 0.1:
        meeting_type = "unknown"
    else:
        # Strongly refinement-leaning?
        if (
            refinement_score >= min_conf_threshold
            and refinement_score >= action_score * dominance_factor
        ):
            meeting_type = "refinement"
        # Strongly action/general-leaning?
        elif (
            action_score >= min_conf_threshold
            and action_score >= refinement_score * dominance_factor
        ):
            meeting_type = "general"
        else:
            meeting_type = "mixed"

    return MeetingClassification(
        meeting_type=meeting_type,
        refinement_score=refinement_score,
        action_score=action_score,
        title_hits=title_hits,
        refinement_hits=refinement_hits,
        action_hits=action_hits,
    )


# --- Example usage ----------------------------------------------------------

if __name__ == "__main__":
    example_title = "Sprint 12 – Backlog Refinement"
    example_transcript = """
    Today we'll refine the backlog, estimate story points,
    and add acceptance criteria in Given/When/Then form.
    We also have a couple of action items around scheduling user interviews.
    """

    result = classify_meeting(example_title, example_transcript)
    print(result.to_dict())
