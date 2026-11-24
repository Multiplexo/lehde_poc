"""Trade overview of the LV and subcontractor suggestions by trade and region."""

import re

from app.models.analysis import Claim
from app.models.lv import LvOrigin, LvPosition, SubcontractorSuggestion, TradeSummary
from app.models.subcontractors import Subcontractor
from app.models.trades import FALLBACK_TRADE, TRADE_BY_CODE, TRADE_CATALOG

MAX_SUGGESTIONS = 5
_POSTAL_CODE = re.compile(r"\b(\d{5})\b")


def project_postal_code(claims: list[Claim]) -> str | None:
    """Postal code of the site from the location statements."""
    for claim in claims:
        if claim.topic != "ort":
            continue
        match = _POSTAL_CODE.search(f"{claim.value} {claim.source.quote}")
        if match:
            return match.group(1)
    return None


def _region(postal_code: str | None, site: str | None) -> tuple[int, str]:
    """Rough proximity from German postal code areas; no geocoding needed."""
    if not postal_code or not site:
        return 3, "Region unbekannt"
    if postal_code[:2] == site[:2]:
        return 0, f"gleiche Region (PLZ {site[:2]}…)"
    if postal_code[:1] == site[:1]:
        return 1, f"Nachbarregion (PLZ-Bereich {site[:1]})"
    return 2, "weiter entfernt"


def suggestions(
    code: str, subcontractors: list[Subcontractor], site: str | None
) -> list[SubcontractorSuggestion]:
    matches = [item for item in subcontractors if code in item.trade_codes]
    ranked = sorted(
        matches, key=lambda item: (_region(item.postal_code, site)[0], item.name)
    )
    return [
        SubcontractorSuggestion(
            subcontractor_id=item.id,
            name=item.name,
            city=item.city,
            postal_code=item.postal_code,
            email=item.email,
            reason=f"Gewerk passt, {_region(item.postal_code, site)[1]}",
        )
        for item in ranked[:MAX_SUGGESTIONS]
    ]


def trade_summaries(
    positions: list[LvPosition], subcontractors: list[Subcontractor], site: str | None
) -> list[TradeSummary]:
    order = {trade.code: index for index, trade in enumerate(TRADE_CATALOG)}
    codes = sorted(
        {
            position.trade_code or FALLBACK_TRADE
            for position in positions
            if position.included
        },
        key=lambda code: order.get(code, 999),
    )
    summaries: list[TradeSummary] = []
    for code in codes:
        trade = TRADE_BY_CODE[code]
        items = [
            position
            for position in positions
            if position.included and (position.trade_code or FALLBACK_TRADE) == code
        ]
        summaries.append(
            TradeSummary(
                code=code,
                label=trade.label,
                own_work=trade.own_work,
                position_count=len(items),
                draft_count=sum(item.origin == LvOrigin.DRAFT for item in items),
                assumption_count=sum(item.assumption is not None for item in items),
                suggestions=[]
                if trade.own_work
                else suggestions(code, subcontractors, site),
            )
        )
    return summaries
