"""
FILE LOCATION: backend/app/schemas/simulation.py
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.simulation import ATTACK_TYPES

AttackType = Literal[
    "brute_force", "dns_tunneling", "phishing", "privilege_escalation", "all"
]
SimulationMode = Literal["fast", "realtime"]
SimulationStatus = Literal["running", "completed", "failed"]


class SimulationRequest(BaseModel):
    attack_type: AttackType
    mode: SimulationMode = "fast"
    noise_events: int = Field(20, ge=0, le=500)
    seed: Optional[int] = None


class SimulationTriggerResponse(BaseModel):
    simulation_id: str
    attack_type: str
    mode: str
    status: SimulationStatus = "running"


class SimulationStatusResponse(BaseModel):
    simulation_id: str
    attack_type: str
    mode: str
    status: SimulationStatus
    events_sent: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None