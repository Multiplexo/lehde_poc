"""Read GAEB DA XML (X81-X86) bills of quantities without a model.

The XML is parsed with defusedxml (no external entities). Each item yields an
OZ built from the category numbers, short text, long text, quantity and unit.
"""

from dataclasses import dataclass
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from app.models.documents import PageLine, PageText

GAEB_CONTENT_TYPE = "application/x-gaeb+xml"
GAEB_SUFFIXES = (".x81", ".x82", ".x83", ".x84", ".x85", ".x86", ".xml")
ITEMS_PER_PAGE = 25


@dataclass
class GaebItem:
    oz: str
    short_text: str
    long_text: str | None
    quantity: float | None
    unit: str | None
    page: int = 0


def is_gaeb(content: bytes, filename: str) -> bool:
    head = content[:4000]
    return filename.lower().endswith(GAEB_SUFFIXES) and b"GAEB" in head


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(element: Element, name: str) -> Element | None:
    return next((child for child in element if _local(child.tag) == name), None)


def _children(element: Element, name: str) -> list[Element]:
    return [child for child in element if _local(child.tag) == name]


def _text(element: Element | None) -> str:
    if element is None:
        return ""
    return " ".join(" ".join(element.itertext()).split())


def _paragraphs(element: Element | None) -> str:
    if element is None:
        return ""
    paragraphs = [
        _text(child) for child in element.iter() if _local(child.tag) in {"p", "div"}
    ]
    paragraphs = [text for text in paragraphs if text]
    return "\n".join(paragraphs) if paragraphs else _text(element)


def _quantity(element: Element) -> float | None:
    raw = _text(_child(element, "Qty"))
    if not raw:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _item(element: Element, prefix: list[str]) -> GaebItem | None:
    number = element.get("RNoPart", "")
    description = _child(element, "Description")
    complete = _child(description, "CompleteText") if description is not None else None
    if complete is None:
        return None
    outline = _child(complete, "OutlineText")
    short = _text(outline)
    detail = _paragraphs(_child(complete, "DetailTxt"))
    if not short:
        short = detail.split("\n", 1)[0][:200]
    if not short:
        return None
    return GaebItem(
        oz=".".join([*prefix, number]).strip("."),
        short_text=short,
        long_text=detail or None,
        quantity=_quantity(element),
        unit=_text(_child(element, "QU")) or None,
    )


def _walk(body: Element, prefix: list[str], items: list[GaebItem]) -> None:
    for category in _children(body, "BoQCtgy"):
        inner = _child(category, "BoQBody")
        if inner is not None:
            _walk(inner, [*prefix, category.get("RNoPart", "")], items)
    for item_list in _children(body, "Itemlist"):
        for element in _children(item_list, "Item"):
            item = _item(element, prefix)
            if item is not None:
                items.append(item)


def parse_gaeb(content: bytes) -> list[GaebItem]:
    root = ElementTree.fromstring(content)
    items: list[GaebItem] = []
    for boq in root.iter():
        if _local(boq.tag) != "BoQ":
            continue
        body = _child(boq, "BoQBody")
        if body is not None:
            _walk(body, [], items)
    if not items:
        raise ValueError("GAEB file contains no items")
    return items


def _format_quantity(item: GaebItem) -> str:
    if item.quantity is None:
        return ""
    value = f"{item.quantity:,.3f}".replace(",", " ").replace(".", ",").rstrip("0")
    return f"{value.rstrip(',')} {item.unit or ''}".strip()


def gaeb_pages(items: list[GaebItem]) -> list[PageText]:
    """Readable pages for the source view and quote grounding."""
    pages: list[PageText] = []
    for start in range(0, len(items), ITEMS_PER_PAGE):
        number = len(pages) + 1
        lines: list[PageLine] = []
        for item in items[start : start + ITEMS_PER_PAGE]:
            item.page = number
            lines.append(PageLine(text=f"{item.oz} {item.short_text}"))
            if item.long_text:
                lines.extend(PageLine(text=line) for line in item.long_text.split("\n"))
            quantity = _format_quantity(item)
            if quantity:
                lines.append(PageLine(text=f"Menge: {quantity}"))
        pages.append(PageText(number=number, lines=lines))
    return pages


def read_gaeb(content: bytes) -> list[PageText]:
    return gaeb_pages(parse_gaeb(content))
