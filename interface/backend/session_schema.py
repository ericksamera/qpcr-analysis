# interface/backend/session_schema.py

from typing import TypedDict
from ddct_pipeline.types import GroupingVariable

class ExperimentConfig(TypedDict):
    genes: list[str]
    reference_genes: list[str]
    grouping_variables: list[GroupingVariable]
    reference_grouping: str
    reference_condition: str
    groups: dict[str, list[str]]
