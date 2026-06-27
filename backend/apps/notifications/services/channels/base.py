from abc import ABC, abstractmethod


class BaseChannel(ABC):
    @abstractmethod
    def send(self, user, tenant, event_type: str, title: str, body: str, entity_type: str = '', entity_id: str = '', metadata: dict = None) -> bool:
        """Deliver a notification. Returns True on success."""
