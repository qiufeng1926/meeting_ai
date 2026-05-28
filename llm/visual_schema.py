"""
图文速览 JSON 结构与校验、版式规范化、长文本分块
"""
import json
import re
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError, field_validator

THEMES = ('green', 'orange', 'blue', 'pink', 'teal', 'brown', 'purple', 'red')
LAYOUTS = ('grid-2', 'grid-3', 'grid-4', 'full')
TAG_LABELS = ('重点', '待跟进', '已决策', '风险', '待确认')
MAX_SECTIONS = 8


class VisualCard(BaseModel):
    title: str = ''
    icon: str = 'doc'
    tag: str | None = None
    bullets: list[str] = Field(default_factory=list)
    highlight: str | None = None

    @field_validator('bullets', mode='before')
    @classmethod
    def coerce_bullets(cls, v):
        return _coerce_str_list(v)


class VisualSection(BaseModel):
    id: str = '1'
    title: str = ''
    theme: str = 'green'
    layout: str = 'grid-3'
    cards: list[VisualCard] = Field(default_factory=list)

    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v: str) -> str:
        return v if v in THEMES else 'green'

    @field_validator('layout')
    @classmethod
    def validate_layout(cls, v: str) -> str:
        return v if v in LAYOUTS else 'grid-3'


def _coerce_str_list(value) -> list[str]:
    """LLM 常把列表字段输出成字符串，统一转为字符串列表"""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parts = re.split(r'[\n；;]+', text)
        if len(parts) == 1 and ('，' in text or ',' in text):
            parts = re.split(r'[，,]+', text)
        return [p.strip() for p in parts if p.strip()]
    return [str(value).strip()] if str(value).strip() else []


class VisualFooter(BaseModel):
    contacts: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    core_consensus: str | None = None

    @field_validator('contacts', 'next_steps', mode='before')
    @classmethod
    def coerce_list_fields(cls, v):
        return _coerce_str_list(v)


class VisualSummary(BaseModel):
    title: str = '会议纪要'
    subtitle: str | None = None
    sections: list[VisualSection] = Field(default_factory=list)
    footer: VisualFooter = Field(default_factory=VisualFooter)


def _extract_json_object(text: str) -> str:
    text = text.strip()
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', text, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def _sanitize_visual_payload(payload: dict) -> dict:
    """校验前修正常见 LLM 输出格式问题"""
    footer = payload.get('footer')
    if isinstance(footer, dict):
        for key in ('contacts', 'next_steps'):
            if key in footer:
                footer[key] = _coerce_str_list(footer.get(key))
    for sec in payload.get('sections') or []:
        if not isinstance(sec, dict):
            continue
        for card in sec.get('cards') or []:
            if isinstance(card, dict) and 'bullets' in card:
                card['bullets'] = _coerce_str_list(card.get('bullets'))
    return payload


def parse_visual_summary(raw: str) -> VisualSummary:
    """解析并校验 LLM 输出的 JSON"""
    payload = json.loads(_extract_json_object(raw))
    payload = _sanitize_visual_payload(payload)
    return VisualSummary.model_validate(payload)


def layout_for_card_count(count: int) -> str:
    if count <= 1:
        return 'full'
    if count == 2:
        return 'grid-2'
    if count <= 4:
        return 'grid-3'
    return 'grid-4'


def normalize_visual_summary(visual: VisualSummary) -> VisualSummary:
    """分区编号 01/02…、按卡片数自动布局、规范 tag"""
    for i, sec in enumerate(visual.sections):
        sec.id = str(i + 1).zfill(2)
        sec.theme = THEMES[i % len(THEMES)]
        n = len(sec.cards)
        sec.layout = layout_for_card_count(n)
        for card in sec.cards:
            if card.tag and card.tag not in TAG_LABELS:
                for label in TAG_LABELS:
                    if label in card.tag:
                        card.tag = label
                        break

    if len(visual.sections) > MAX_SECTIONS:
        visual.sections = visual.sections[:MAX_SECTIONS]

    return visual


def split_transcript_chunks(text: str, max_chars: int, overlap: int = 400) -> list[str]:
    """按段落合并为不超过 max_chars 的块，块间保留 overlap 字符避免断句"""
    text = (text or '').strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if not paragraphs:
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars - overlap)]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush():
        nonlocal current, current_len
        if current:
            chunks.append('\n\n'.join(current))
            current = []
            current_len = 0

    for para in paragraphs:
        plen = len(para) + 2
        if plen > max_chars:
            flush()
            for i in range(0, len(para), max_chars - overlap):
                chunks.append(para[i:i + max_chars])
            continue
        if current_len + plen > max_chars and current:
            flush()
            if chunks and overlap > 0:
                tail = chunks[-1][-overlap:].strip()
                if tail:
                    current = [tail]
                    current_len = len(tail) + 2
        current.append(para)
        current_len += plen

    flush()
    return chunks if chunks else [text[:max_chars]]


def _dedupe_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def merge_visual_parts(parts: list[VisualSummary]) -> VisualSummary:
    """合并多段图文结果"""
    if not parts:
        return VisualSummary()
    if len(parts) == 1:
        return parts[0]

    title = parts[0].title or '会议纪要'
    subtitle = parts[0].subtitle
    sections: list[VisualSection] = []
    all_contacts: list[str] = []
    all_steps: list[str] = []
    consensuses: list[str] = []

    for part in parts:
        sections.extend(part.sections)
        all_contacts.extend(part.footer.contacts or [])
        all_steps.extend(part.footer.next_steps or [])
        if part.footer.core_consensus:
            consensuses.append(part.footer.core_consensus.strip())

    if len(consensuses) > 1:
        core = ' '.join(consensuses[:2])
    elif consensuses:
        core = consensuses[0]
    else:
        core = None

    return VisualSummary(
        title=title,
        subtitle=subtitle,
        sections=sections,
        footer=VisualFooter(
            contacts=_dedupe_ordered(all_contacts),
            next_steps=_dedupe_ordered(all_steps),
            core_consensus=core,
        ),
    )


def visual_summary_to_dict(summary: VisualSummary) -> dict[str, Any]:
    return summary.model_dump()


def visual_summary_to_json(summary: VisualSummary) -> str:
    return json.dumps(summary.model_dump(), ensure_ascii=False)


async def parse_visual_summary_with_repair(
    raw: str,
    repair_fn: Callable[[str], Any] | None = None,
) -> VisualSummary:
    """解析 JSON，失败时可选调用 repair_fn 修复后再解析"""
    try:
        visual = parse_visual_summary(raw)
    except (json.JSONDecodeError, ValueError, ValidationError) as first_error:
        if not repair_fn:
            raise first_error
        repaired_raw = await repair_fn(raw)
        visual = parse_visual_summary(repaired_raw)
    return normalize_visual_summary(visual)
