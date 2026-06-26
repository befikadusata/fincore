import importlib
import logging

logger = logging.getLogger(__name__)


class EventRegistry:
    """
    In-memory mapping of event_type → list[callable].
    Populated lazily from DB on first handler lookup, and via register().
    """
    _handlers: dict[str, list[str]] = {}
    _db_loaded: bool = False

    @classmethod
    def register(cls, event_type: str, handler_path: str) -> None:
        cls._handlers.setdefault(event_type, [])
        if handler_path not in cls._handlers[event_type]:
            cls._handlers[event_type].append(handler_path)

    @classmethod
    def get_handlers(cls, event_type: str) -> list:
        if not cls._db_loaded:
            cls.load_from_db()
        paths = cls._handlers.get(event_type, [])
        handlers = []
        for path in paths:
            try:
                module_path, func_name = path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                handlers.append(getattr(module, func_name))
            except Exception:
                logger.exception('Failed to load handler: %s', path)
        return handlers

    @classmethod
    def load_from_db(cls) -> None:
        """Load all active subscriptions from DB into the in-memory registry."""
        from apps.events.models import EventSubscription
        try:
            for sub in EventSubscription.objects.filter(is_active=True):
                cls.register(sub.event_type, sub.handler_path)
            cls._db_loaded = True
        except Exception:
            logger.debug('EventRegistry.load_from_db skipped — DB not ready')

    @classmethod
    def clear(cls) -> None:
        """Reset registry — used in tests."""
        cls._handlers = {}
        cls._db_loaded = False
