"""
Heuristic for flagging a detected vehicle as (likely) supporting a
reported parking violation.

**Important limitation, stated plainly:** a single photo has no reliable
way to confirm a vehicle is in a no-parking zone, blocking an emergency
exit, etc. Doing that properly would need either (a) geo-referencing the
exact camera position/angle against known zone geometry — a much harder
photogrammetry problem, out of scope here — or (b) a human reviewing the
photo. This heuristic does *not* attempt (a). What it actually does is
flag whether a vehicle was detected with enough confidence to be useful
supporting evidence for the complaint it was attached to.

Practical effect: treat `is_illegal_parking=True` as "worth an officer's
attention", not "confirmed violation". This is a deliberate, documented
simplification — not a limitation to quietly work around.
"""

from typing import Optional, Tuple

DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.5


def assess_detection(
    vehicle_class: str,
    confidence: float,
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
) -> Tuple[Optional[bool], str]:
    """Returns (is_illegal_parking, reason). `is_illegal_parking` is a
    heuristic confidence gate, not an independently verified violation —
    see the module docstring."""
    if confidence >= high_confidence_threshold:
        return True, (
            f"{vehicle_class.capitalize()} detected with {confidence:.0%} confidence — "
            "supports the reported violation; final determination requires officer review."
        )
    return False, (
        f"{vehicle_class.capitalize()} detected but with only {confidence:.0%} confidence — "
        "flagged for manual review rather than treated as supporting evidence."
    )
