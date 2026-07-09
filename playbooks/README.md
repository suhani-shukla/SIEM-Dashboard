# SIEM Playbooks

This directory contains YAML-driven attack playbooks mapped to MITRE ATT&CK for the SIEM Correlation Engine.
Playbooks define rules to detect malicious behavior in the incoming event streams.

## YAML Schema

A playbook requires the following fields:

- `name` (string): A unique identifier for the playbook.
- `description` (string): Description of the detection.
- `mitre_attack` (object):
  - `technique_id` (string): e.g., "T1110".
  - `technique_name` (string): e.g., "Brute Force".
  - `tactic` (string): e.g., "Credential Access".
- `rule_type` (string): One of `threshold`, `sequence`, or `aggregation`.
- `enabled` (boolean): Default state on load.
- `severity` (string): e.g., "low", "medium", "high", "critical".

Depending on the `rule_type`, additional fields are required:

### Threshold Rule (`threshold`)
Triggers when an event matches the `match` criteria `count` times within `window_seconds`.
- `match` (object): Key-value pairs to match against events.
- `threshold`:
  - `count` (integer)
  - `window_seconds` (integer)
  - `group_by` (string): Field to aggregate on, e.g., "source".

### Sequence Rule (`sequence`)
Triggers when a specific ordered list of `steps` occurs within `window_seconds`.
- `steps` (list of objects): Ordered match criteria.
- `threshold`:
  - `window_seconds` (integer)
  - `group_by` (string)

### Aggregation Rule (`aggregation`)
Triggers when the distinct count of an `aggregate_field` crosses `threshold.count` within `window_seconds`.
- `match` (object): Key-value pairs to match against events.
- `threshold`:
  - `count` (integer)
  - `window_seconds` (integer)
  - `group_by` (string)
- `aggregate_field` (string): The field to count distinct occurrences of.
