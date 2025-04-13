# ddct_pipeline/models.py

from dataclasses import dataclass
from typing import List

@dataclass
class CtRow:
    sample_id: str
    gene: str
    ct: float  # ✅ always averaged
    metadata: dict[str, str]


@dataclass
class GroupingVariable:
    name: str
    acceptable_values: List[str]