import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.playbook_override import PlaybookOverride
from app.playbooks.loader import PLAYBOOKS_DIR, load_playbooks
from app.schemas.playbook import PlaybookConfig, playbook_adapter

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


class PlaybookToggle(BaseModel):
    enabled: bool


@router.get("", response_model=list[PlaybookConfig])
async def list_playbooks(db: AsyncSession = Depends(get_db)):
    if not PLAYBOOKS_DIR.exists():
        return []

    result = await db.execute(select(PlaybookOverride))
    overrides = {row.name: row.enabled for row in result.scalars()}

    playbooks = []
    for file_path in PLAYBOOKS_DIR.glob("*.yaml"):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                playbook = playbook_adapter.validate_python(data)
                if playbook.name in overrides:
                    playbook.enabled = overrides[playbook.name]
                playbooks.append(playbook)
            except Exception:
                continue

    return playbooks


@router.get("/{name}", response_model=PlaybookConfig)
async def get_playbook(name: str, db: AsyncSession = Depends(get_db)):
    file_path = PLAYBOOKS_DIR / f"{name}.yaml"
    if not file_path.exists():
        # Try to find it by name inside the files if filename doesn't match
        found = False
        for fp in PLAYBOOKS_DIR.glob("*.yaml"):
            with open(fp, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and data.get("name") == name:
                    file_path = fp
                    found = True
                    break
        if not found:
            raise HTTPException(status_code=404, detail="Playbook not found")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        playbook = playbook_adapter.validate_python(data)

    result = await db.execute(select(PlaybookOverride).where(PlaybookOverride.name == playbook.name))
    override = result.scalars().first()
    if override:
        playbook.enabled = override.enabled

    return playbook


@router.patch("/{name}", response_model=PlaybookConfig)
async def toggle_playbook(
    name: str,
    payload: PlaybookToggle,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Ensure playbook exists
    playbook = await get_playbook(name, db)

    # Update or create override
    result = await db.execute(select(PlaybookOverride).where(PlaybookOverride.name == playbook.name))
    override = result.scalars().first()
    
    if override:
        override.enabled = payload.enabled
    else:
        override = PlaybookOverride(name=playbook.name, enabled=payload.enabled)
        db.add(override)
        
    await db.commit()

    # Reload rules dynamically
    rules = await load_playbooks(db)
    request.app.state.rule_engine.update_rules(rules)

    playbook.enabled = payload.enabled
    return playbook
