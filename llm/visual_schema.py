"""
图文速览 JSON 结构与校验
"""
import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

THEMES = ('green', 'orange', 'blue', 'pink', 'teal', 'brown', 'purple', 'red')
LAYOUTS = ('grid-2', 'grid-3', 'grid-4', 'full')


class VisualCard(BaseModel):
    title: str = ''
    icon: str = 'doc'
    tag: str | None = None
    bullets: list[str] = Field(default_factory=list)
    highlight: str | None = None


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


class VisualFooter(BaseModel):
    contacts: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    core_consensus: str | None = None


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


def parse_visual_summary(raw: str) -> VisualSummary:
    """解析并校验 LLM 输出的 JSON"""
    payload = json.loads(_extract_json_object(raw))
    return VisualSummary.model_validate(payload)


def visual_summary_to_dict(summary: VisualSummary) -> dict[str, Any]:
    return summary.model_dump()


def visual_summary_to_json(summary: VisualSummary) -> str:
    return json.dumps(summary.model_dump(), ensure_ascii=False)
