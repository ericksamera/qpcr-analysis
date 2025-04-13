# ddct_pipeline/types.py

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class CtRow:
    sample_id: str
    gene: str
    ct: float
    metadata: Dict[str, str]

@dataclass
class GroupingVariable:
    name: str
    values: List[str]
