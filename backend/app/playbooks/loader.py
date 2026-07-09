import os
import yaml
from pathlib import Path
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.playbook import PlaybookConfig, playbook_adapter
from app.models.playbook_override import PlaybookOverride
from app.rules.base import Rule
from app.rules.threshold import ThresholdRule
from app.rules.sequence import SequenceRule
from app.rules.aggregation import AggregationRule

PLAYBOOKS_DIR = Path(__file__).parent.parent.parent.parent / "playbooks"


async def load_playbooks(db: AsyncSession) -> list[Rule]:
    if not PLAYBOOKS_DIR.exists():
        return []

    # Get overrides from DB
    result = await db.execute(select(PlaybookOverride))
    overrides = {row.name: row.enabled for row in result.scalars()}

    rules: list[Rule] = []

    for file_path in PLAYBOOKS_DIR.glob("*.yaml"):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                if not data:
                    continue
                playbook = playbook_adapter.validate_python(data)
            except ValidationError as e:
                raise ValueError(f"Playbook {file_path.name} is malformed: {e}")
            except Exception as e:
                raise ValueError(f"Failed to read playbook {file_path.name}: {e}")

        # Check enabled state
        is_enabled = overrides.get(playbook.name, playbook.enabled)
        if not is_enabled:
            continue

        base_config = {
            "rule_name": playbook.name,
            "mitre_technique": playbook.mitre_attack.technique_id,
            "severity": playbook.severity,
            "window_seconds": playbook.threshold.window_seconds,
            "group_by": playbook.threshold.group_by,
        }

        if playbook.rule_type == "threshold":
            config = {
                **base_config,
                "match": playbook.match,
                "count": playbook.threshold.count,
            }
            rules.append(ThresholdRule(config))
        elif playbook.rule_type == "sequence":
            config = {
                **base_config,
                "steps": playbook.steps,
            }
            rules.append(SequenceRule(config))
        elif playbook.rule_type == "aggregation":
            config = {
                **base_config,
                "match": playbook.match,
                "aggregate_field": playbook.aggregate_field,
                "threshold": playbook.threshold.count,
            }
            rules.append(AggregationRule(config))

    return rules
