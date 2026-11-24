import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

import structlog

from app.models.analysis import (
    Claim,
    Discrepancy,
    DiscrepancyKind,
    DiscrepancySide,
    Fact,
    FactStatus,
    ProjectSummary,
    Recipient,
    Severity,
)
from app.models.catalog import FACT_BY_KEY, FACT_CATALOG
from app.services.ai import AIService, UsageCounter, text_part
from app.services.pipeline.prompts import CONSOLIDATION_INSTRUCTIONS
from app.services.pipeline.schemas import ConsolidationResult

logger = structlog.get_logger(__name__)


@dataclass
class Consolidation:
    facts: list[Fact]
    discrepancies: list[Discrepancy]
    summary: ProjectSummary | None


def _content_id(topic: str, claim_a: Claim, claim_b: Claim) -> str:
    sides = sorted(
        [
            f"{claim_a.document_id}:{claim_a.source.quote}",
            f"{claim_b.document_id}:{claim_b.source.quote}",
        ]
    )
    digest = hashlib.sha1("|".join([topic, *sides]).encode()).hexdigest()[:10]
    return f"c-{digest}"


def _side(claim: Claim) -> DiscrepancySide:
    return DiscrepancySide(
        document_id=claim.document_id, value=claim.value, source=claim.source
    )


def build_facts(
    claims: list[Claim],
    values: dict[str, tuple[str, list[str]]],
    discrepancies: list[Discrepancy],
) -> list[Fact]:
    by_id = {claim.id: claim for claim in claims}
    conflict_topics = {item.topic for item in discrepancies}
    facts: list[Fact] = []
    for definition in FACT_CATALOG:
        topic_claims = [claim for claim in claims if claim.topic == definition.key]
        consolidated = values.get(definition.key)
        if consolidated is not None:
            value, claim_ids = consolidated
            supporting = [
                by_id[claim_id] for claim_id in claim_ids if claim_id in by_id
            ]
            # Keep all claims of the topic visible, supporting ones first.
            supporting += [claim for claim in topic_claims if claim not in supporting]
        else:
            supporting = topic_claims
            value = "; ".join(claim.value for claim in topic_claims) or None
        if not supporting:
            facts.append(
                Fact(
                    key=definition.key,
                    label=definition.label,
                    group=definition.group,
                    status=FactStatus.NOT_FOUND,
                )
            )
            continue
        facts.append(
            Fact(
                key=definition.key,
                label=definition.label,
                group=definition.group,
                status=FactStatus.CONFLICT
                if definition.key in conflict_topics
                else FactStatus.FOUND,
                value=value,
                claims=supporting,
            )
        )
    return facts


async def consolidate(
    ai: AIService,
    usage: UsageCounter,
    claims: list[Claim],
    document_names: dict[UUID, str],
) -> Consolidation:
    if not claims:
        return Consolidation(
            facts=build_facts([], {}, []), discrepancies=[], summary=None
        )
    by_id = {claim.id: claim for claim in claims}
    payload = [
        {
            "id": claim.id,
            "dokument": document_names.get(claim.document_id, "Dokument"),
            "topic": claim.topic,
            "thema": FACT_BY_KEY[claim.topic].label,
            "value": claim.value,
            "quote": claim.source.quote,
        }
        for claim in claims
    ]
    result = await ai.parse(
        task="consolidation",
        instructions=CONSOLIDATION_INSTRUCTIONS,
        content=[text_part(json.dumps(payload, ensure_ascii=False, indent=1))],
        schema=ConsolidationResult,
        usage=usage,
    )

    values: dict[str, tuple[str, list[str]]] = {}
    for fact in result.facts:
        valid_ids = [claim_id for claim_id in fact.claim_ids if claim_id in by_id]
        if fact.topic in FACT_BY_KEY and valid_ids:
            values[fact.topic] = (fact.value.strip(), valid_ids)

    discrepancies: list[Discrepancy] = []
    seen: set[str] = set()
    for item in result.discrepancies:
        claim_a, claim_b = by_id.get(item.claim_a), by_id.get(item.claim_b)
        if claim_a is None or claim_b is None or claim_a.id == claim_b.id:
            logger.info("discrepancy_dropped_unknown_claims", topic=item.topic)
            continue
        topic = item.topic if item.topic in FACT_BY_KEY else claim_a.topic
        discrepancy_id = _content_id(topic, claim_a, claim_b)
        if discrepancy_id in seen:
            continue
        seen.add(discrepancy_id)
        discrepancies.append(
            Discrepancy(
                id=discrepancy_id,
                kind=DiscrepancyKind.CONTENT,
                topic=topic,
                title=item.title.strip(),
                explanation=item.explanation.strip(),
                severity=Severity(item.severity),
                side_a=_side(claim_a),
                side_b=_side(claim_b),
                recipient=Recipient(item.recipient),
                question=item.question.strip(),
            )
        )

    summary_ids = [
        claim_id for claim_id in result.summary.claim_ids if claim_id in by_id
    ]
    summary = (
        ProjectSummary(text=result.summary.text.strip(), claim_ids=summary_ids)
        if summary_ids and result.summary.text.strip()
        else None
    )
    logger.info(
        "consolidation_completed",
        fact_count=len(values),
        discrepancy_count=len(discrepancies),
        dropped_discrepancies=len(result.discrepancies) - len(discrepancies),
    )
    return Consolidation(
        facts=build_facts(claims, values, discrepancies),
        discrepancies=discrepancies,
        summary=summary,
    )
