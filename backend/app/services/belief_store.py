from __future__ import annotations
from typing import Optional, Dict
from app.models.role_profile import BeliefParameter
from app.models.user_belief import UserBelief

_beliefs: Dict[str, Dict[BeliefParameter, UserBelief]] = {}
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"

def get_beliefs(user_id: str = DEFAULT_USER_ID) -> Optional[Dict[BeliefParameter, UserBelief]]:
    return _beliefs.get(user_id)

def set_beliefs(beliefs: Dict[BeliefParameter, UserBelief], user_id: str = DEFAULT_USER_ID) -> None:
    _beliefs[user_id] = beliefs

def update_beliefs(updated: Dict[BeliefParameter, UserBelief], user_id: str = DEFAULT_USER_ID) -> None:
    existing = _beliefs.get(user_id, {})
    existing.update(updated)
    _beliefs[user_id] = existing
