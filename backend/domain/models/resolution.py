"""
Domain models for HITL resolution options.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass
class ResolutionAction:
    type: str # e.g. "update_budget", "append_reason", "retry"
    value: str

@dataclass
class ResolutionOption:
    id: str
    label: str
    action: ResolutionAction
