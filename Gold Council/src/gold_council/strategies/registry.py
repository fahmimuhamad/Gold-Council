"""Versioned strategy registry. Promotion beyond `draft` is a human action, never automatic."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

Status = Literal["draft", "reviewed", "research_approved", "paper_approved", "disabled"]
CANDIDATE_STATUSES = {"research_approved", "paper_approved"}


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    location: str           # page / timestamp / section
    note: str = ""


class StrategyDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    spec_id: str                    # S01..S22
    version: str
    status: Status
    family: str
    instrument: str = "XAUUSD"
    setup_tf: str
    context_tf: str | None = None
    detector: str | None = None     # name in strategies.detectors.DETECTORS
    parameters: dict = Field(default_factory=dict)
    source_refs: list[SourceRef] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    approved_by: str | None = None
    approved_at: str | None = None

    def can_emit_candidates(self) -> bool:
        return (self.status in CANDIDATE_STATUSES and not self.unresolved
                and bool(self.source_refs) and bool(self.approved_by))


def load_registry(folder: str | Path) -> list[StrategyDef]:
    out = []
    for p in sorted(Path(folder).glob("*.yaml")):
        with open(p, encoding="utf-8") as fh:
            out.append(StrategyDef.model_validate(yaml.safe_load(fh)))
    ids = [s.id for s in out]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate strategy ids: {sorted(dupes)}")
    return out


def validate_registry(defs: list[StrategyDef]) -> list[str]:
    """Return problems. Approved statuses need sources, reviewer and no unresolved items."""
    from gold_council.strategies.detectors import DETECTORS
    problems = []
    for s in defs:
        if s.detector and s.detector not in DETECTORS:
            problems.append(f"{s.id}: unknown detector {s.detector}")
        if s.status in CANDIDATE_STATUSES | {"reviewed"}:
            if not s.source_refs:
                problems.append(f"{s.id}: status {s.status} without source_refs")
            if s.unresolved:
                problems.append(f"{s.id}: status {s.status} with unresolved items")
            if s.status in CANDIDATE_STATUSES and not s.approved_by:
                problems.append(f"{s.id}: status {s.status} without human approver")
    return problems
