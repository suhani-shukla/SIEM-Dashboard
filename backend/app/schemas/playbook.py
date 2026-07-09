from typing import Any, Literal

from pydantic import BaseModel, Field, TypeAdapter


class MitreAttack(BaseModel):
    technique_id: str
    technique_name: str
    tactic: str


class ThresholdConfig(BaseModel):
    count: int | None = None
    window_seconds: int
    group_by: str


class BasePlaybookConfig(BaseModel):
    name: str
    description: str
    mitre_attack: MitreAttack
    enabled: bool = True
    severity: str


class ThresholdRuleConfig(BasePlaybookConfig):
    rule_type: Literal["threshold"]
    match: dict[str, Any]
    threshold: ThresholdConfig


class SequenceRuleConfig(BasePlaybookConfig):
    rule_type: Literal["sequence"]
    steps: list[dict[str, Any]]
    threshold: ThresholdConfig


class AggregationRuleConfig(BasePlaybookConfig):
    rule_type: Literal["aggregation"]
    match: dict[str, Any]
    aggregate_field: str
    threshold: ThresholdConfig


PlaybookConfig = ThresholdRuleConfig | SequenceRuleConfig | AggregationRuleConfig

playbook_adapter = TypeAdapter(PlaybookConfig)
