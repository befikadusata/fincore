from typing import Dict, List, Any
from core.exceptions import InvalidStateTransitionError


class StateMachine:
    """Generic state machine utility to handle safe model field transitions."""
    def __init__(self, transitions: Dict[str, List[str]]):
        self.transitions = transitions

    def transition(self, instance: Any, field_name: str, to_state: str) -> Any:
        current_state = getattr(instance, field_name)
        allowed = self.transitions.get(current_state, [])
        if to_state not in allowed:
            raise InvalidStateTransitionError(current_state, to_state)

        setattr(instance, field_name, to_state)
        instance.save(update_fields=[field_name])
        return instance

    def get_available_transitions(self, current_state: str) -> List[str]:
        return self.transitions.get(current_state, [])
