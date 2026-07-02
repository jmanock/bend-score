from __future__ import annotations

import importlib
import pkgutil

from bend_score.config import OBSERVER_CONFIG_PATH
import bend_score.observers
from bend_score.observers.base import Observer
from bend_score.utils.config_loader import load_observer_config


class ObserverRegistry:
    _observers: dict[str, type[Observer]] = {}

    @classmethod
    def register(cls, observer_cls: type[Observer]) -> None:
        cls._observers[observer_cls.name] = observer_cls

    @classmethod
    def all(cls) -> dict[str, type[Observer]]:
        _import_observers()
        return dict(cls._observers)

    @classmethod
    def enabled(cls) -> list[Observer]:
        config = load_observer_config(OBSERVER_CONFIG_PATH)
        enabled: list[Observer] = []
        for name, observer_cls in cls.all().items():
            observer_config = config.get(name, {})
            if observer_config.get("enabled", False):
                enabled.append(observer_cls())
        return enabled


def _import_observers() -> None:
    for module in pkgutil.iter_modules(bend_score.observers.__path__):
        if module.name in {"base", "registry"}:
            continue
        importlib.import_module(f"bend_score.observers.{module.name}")
