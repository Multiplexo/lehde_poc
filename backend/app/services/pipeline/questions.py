"""Build the list of questions to architect and client (Rückfrageliste)."""

from app.models.analysis import (
    Discrepancy,
    DiscrepancyStatus,
    Fact,
    FactStatus,
    Question,
    Recipient,
)
from app.models.catalog import FACT_BY_KEY

MISSING_FACT_RECIPIENTS: dict[str, Recipient] = {
    "bauherr": Recipient.BAUHERR,
    "termine": Recipient.BAUHERR,
    "leistungsgrenzen": Recipient.BAUHERR,
    "bodenaufbau": Recipient.BAUHERR,
    "grundwasser": Recipient.BAUHERR,
    "kontaminationen": Recipient.BAUHERR,
    "genehmigungsauflagen": Recipient.BAUHERR,
}
CLOSED_STATUSES = {DiscrepancyStatus.DONE, DiscrepancyStatus.RESERVATION}


def _discrepancy_question(item: Discrepancy) -> Question:
    sources = [
        side.source for side in (item.side_a, item.side_b) if side and side.source
    ]
    return Question(
        id=f"q-{item.id}",
        text=item.question,
        recipient=item.recipient,
        included=item.status not in CLOSED_STATUSES
        and item.recipient != Recipient.KALKULATION,
        discrepancy_id=item.id,
        sources=sources,
    )


def _missing_question(fact: Fact) -> Question:
    definition = FACT_BY_KEY[fact.key]
    return Question(
        id=f"q-missing-{fact.key}",
        text=(
            f"In den Anfrageunterlagen haben wir keine Angaben zu „{definition.label}“ "
            "gefunden. Bitte ergänzen Sie diese Information oder nennen Sie uns das "
            "Dokument, in dem sie steht."
        ),
        recipient=MISSING_FACT_RECIPIENTS.get(fact.key, Recipient.ARCHITEKT),
        included=definition.onepager,
        fact_key=fact.key,
    )


def build_questions(
    discrepancies: list[Discrepancy],
    facts: list[Fact],
    previous: list[Question],
) -> list[Question]:
    """Derive questions; keep edits from an earlier run for the same item."""
    earlier = {question.id: question for question in previous}
    questions = [_discrepancy_question(item) for item in discrepancies]
    questions += [
        _missing_question(fact) for fact in facts if fact.status == FactStatus.NOT_FOUND
    ]
    merged: list[Question] = []
    for question in questions:
        old = earlier.get(question.id)
        if old is not None:
            question = question.model_copy(
                update={
                    "text": old.text,
                    "included": old.included,
                    "recipient": old.recipient,
                }
            )
        merged.append(question)
    return merged


def sync_discrepancy_question(
    questions: list[Question], item: Discrepancy
) -> list[Question]:
    updated = _discrepancy_question(item)
    result = [
        updated if question.discrepancy_id == item.id else question
        for question in questions
    ]
    if not any(question.discrepancy_id == item.id for question in questions):
        result.insert(0, updated)
    return result
