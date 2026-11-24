"""Rule-based plan revision check (Planstand).

Compares the plans in the package (read from title blocks) with every plan a
document refers to. This check runs without a model so that revision mismatches
are found reliably.
"""

import hashlib
import re
from uuid import UUID

from app.models.analysis import (
    Discrepancy,
    DiscrepancyKind,
    DiscrepancySide,
    PlanReference,
    Recipient,
    Severity,
)
from app.models.documents import PlanEntry

_REVISION_PATTERN = re.compile(
    r"(?:INDEX|IND\.?|REVISION|REV\.?|PLANSTAND|STAND|VERSION)\s*[:.]?\s*([A-Z0-9]{1,3})\b"
)
_SHORT_REVISION = re.compile(r"^[A-Z0-9]{1,3}$")


def plan_key(plan_number: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", plan_number.upper())


def revision_key(revision: str | None) -> str | None:
    if not revision:
        return None
    text = revision.upper().strip()
    if _SHORT_REVISION.match(text):
        return text.lstrip("0") or "0"
    match = _REVISION_PATTERN.search(text)
    if match:
        return match.group(1).lstrip("0") or "0"
    compact = re.sub(r"[^0-9A-Z]", "", text)
    return compact or None


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]
    return f"p-{digest}"


def _index(revision: str | None) -> str:
    """Readable revision: "B" becomes "Index B", "Rev. 03" stays as written."""
    text = (revision or "").strip()
    if not text:
        return "ohne Index"
    return f"Index {text}" if _SHORT_REVISION.match(text.upper()) else text


def _plan_label(number: str, revision: str | None) -> str:
    return f"Plan {number}, {_index(revision)}" if revision else f"Plan {number}"


def check_plan_revisions(
    register: list[PlanEntry],
    references: list[PlanReference],
    document_names: dict[UUID, str],
) -> list[Discrepancy]:
    discrepancies: list[Discrepancy] = []
    by_number: dict[str, list[PlanEntry]] = {}
    for entry in register:
        by_number.setdefault(plan_key(entry.plan_number), []).append(entry)

    for key, entries in by_number.items():
        revisions = {revision_key(entry.revision) for entry in entries} - {None}
        if len(revisions) < 2:
            continue
        first, second = (
            entries[0],
            next(
                entry
                for entry in entries[1:]
                if revision_key(entry.revision) != revision_key(entries[0].revision)
            ),
        )
        discrepancies.append(
            Discrepancy(
                id=_stable_id("double", key),
                kind=DiscrepancyKind.PLANSTAND,
                topic="planstand",
                title=f"Plan {first.plan_number} liegt in mehreren Ständen vor",
                explanation=(
                    "Im Paket liegen zwei Fassungen desselben Plans mit "
                    "unterschiedlichem Index. Unklar ist, welche gilt."
                ),
                severity=Severity.RED,
                side_a=DiscrepancySide(
                    document_id=first.document_id,
                    value=_plan_label(first.plan_number, first.revision),
                    source=first.source,
                ),
                side_b=DiscrepancySide(
                    document_id=second.document_id,
                    value=_plan_label(second.plan_number, second.revision),
                    source=second.source,
                ),
                recipient=Recipient.ARCHITEKT,
                question=(
                    f"Plan {first.plan_number} liegt uns mit {_index(first.revision)} "
                    f"und {_index(second.revision)} vor. Welcher Planstand ist "
                    "für die Angebotsbearbeitung verbindlich?"
                ),
            )
        )

    missing_reported: set[tuple[UUID, str]] = set()
    unmatched: dict[str, list[PlanReference]] = {}
    for reference in references:
        key = plan_key(reference.plan_number)
        if not key:
            continue
        document_name = document_names.get(reference.document_id, "Dokument")
        entries = by_number.get(key)
        if not entries:
            unmatched.setdefault(key, []).append(reference)
            if register and (reference.document_id, key) not in missing_reported:
                missing_reported.add((reference.document_id, key))
                discrepancies.append(
                    Discrepancy(
                        id=_stable_id("missing", str(reference.document_id), key),
                        kind=DiscrepancyKind.PLANSTAND,
                        topic="planstand",
                        title=f"Plan {reference.plan_number} fehlt im Paket",
                        explanation=(
                            f"{document_name} verweist auf diesen Plan, er ist "
                            "aber nicht Teil der Anfrageunterlagen."
                        ),
                        severity=Severity.YELLOW,
                        side_a=DiscrepancySide(
                            document_id=reference.document_id,
                            value=_plan_label(
                                reference.plan_number, reference.revision
                            ),
                            source=reference.source,
                        ),
                        recipient=Recipient.ARCHITEKT,
                        question=(
                            f"{document_name} verweist auf Plan "
                            f"{reference.plan_number}, der den Unterlagen nicht "
                            "beiliegt. Bitte senden Sie uns den Plan im aktuellen "
                            "Stand."
                        ),
                    )
                )
            continue
        expected = revision_key(reference.revision)
        if expected is None:
            continue
        if any(revision_key(entry.revision) == expected for entry in entries):
            continue
        entry = next(
            (item for item in entries if revision_key(item.revision)), entries[0]
        )
        discrepancies.append(
            Discrepancy(
                id=_stable_id("revision", reference.id, key),
                kind=DiscrepancyKind.PLANSTAND,
                topic="planstand",
                title=f"Planstand {reference.plan_number} abweichend",
                explanation=(
                    f"{document_name} bezieht sich auf {_index(reference.revision)}, "
                    f"im Paket liegt der Plan mit {_index(entry.revision)}."
                ),
                severity=Severity.RED,
                side_a=DiscrepancySide(
                    document_id=reference.document_id,
                    value=_plan_label(reference.plan_number, reference.revision),
                    source=reference.source,
                ),
                side_b=DiscrepancySide(
                    document_id=entry.document_id,
                    value=_plan_label(entry.plan_number, entry.revision),
                    source=entry.source,
                ),
                recipient=Recipient.ARCHITEKT,
                question=(
                    f"{document_name} bezieht sich auf Plan {reference.plan_number} "
                    f"{_index(reference.revision)}, beigefügt ist "
                    f"{_index(entry.revision)}. Welcher Planstand gilt, und wird "
                    f"{document_name} auf den aktuellen Stand fortgeschrieben?"
                ),
            )
        )

    for key, items in unmatched.items():
        with_revision = [item for item in items if revision_key(item.revision)]
        first = with_revision[0] if with_revision else None
        if first is None:
            continue
        other = next(
            (
                item
                for item in with_revision[1:]
                if revision_key(item.revision) != revision_key(first.revision)
            ),
            None,
        )
        if other is None:
            continue
        name_a = document_names.get(first.document_id, "Dokument")
        name_b = document_names.get(other.document_id, "Dokument")
        discrepancies.append(
            Discrepancy(
                id=_stable_id("references", key, first.id, other.id),
                kind=DiscrepancyKind.PLANSTAND,
                topic="planstand",
                title=f"Unterschiedliche Planstände für {first.plan_number}",
                explanation=(
                    f"{name_a} und {name_b} beziehen sich auf unterschiedliche "
                    "Indizes desselben Plans."
                ),
                severity=Severity.RED if register else Severity.YELLOW,
                side_a=DiscrepancySide(
                    document_id=first.document_id,
                    value=_plan_label(first.plan_number, first.revision),
                    source=first.source,
                ),
                side_b=DiscrepancySide(
                    document_id=other.document_id,
                    value=_plan_label(other.plan_number, other.revision),
                    source=other.source,
                ),
                recipient=Recipient.ARCHITEKT,
                question=(
                    f"{name_a} nennt für Plan {first.plan_number} "
                    f"{_index(first.revision)}, {name_b} {_index(other.revision)}. Welcher "
                    "Planstand ist verbindlich?"
                ),
            )
        )
    return discrepancies
