import importlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Literal

from app.schemas.common import Meta

log = logging.getLogger(__name__)
PUBLIC_FALLBACK_WARNING = "Some insights are temporarily unavailable. Showing a backup estimate."


@dataclass
class GatewayOutcome:
    value: Any
    source: Literal["model", "baseline"]
    warning: str | None = None


class Gateway:
    def __init__(self, mode: str = "auto", package: str = "intelligence"):
        self.mode = mode
        self.package = package

    def run(self, module: str, func: str, baseline: Callable, *args,
            expect: type | None = None, **kwargs) -> GatewayOutcome:
        if self.mode == "baseline":
            return GatewayOutcome(baseline(*args, **kwargs), "baseline")
        name = f"{self.package}.{module}"
        try:
            fn = getattr(importlib.import_module(name), func, None)
        except ModuleNotFoundError as exc:
            if exc.name in (name, self.package):
                fn = None
            else:
                return self._fallback(baseline, args, kwargs, f"{name} import failed ({type(exc).__name__})")
        except Exception as exc:
            return self._fallback(baseline, args, kwargs, f"{name} import failed ({type(exc).__name__})")
        if fn is None:
            return GatewayOutcome(baseline(*args, **kwargs), "baseline")
        try:
            value = fn(*args, **kwargs)
        except Exception as exc:
            return self._fallback(baseline, args, kwargs, f"{name}.{func} failed ({type(exc).__name__})")
        if expect is not None and not isinstance(value, expect):
            return self._fallback(baseline, args, kwargs,
                                  f"{name}.{func} returned {type(value).__name__}, "
                                  f"expected {expect.__name__}")
        return GatewayOutcome(value, "model")

    @staticmethod
    def _fallback(baseline, args, kwargs, warning: str) -> GatewayOutcome:
        log.warning(warning)
        return GatewayOutcome(baseline(*args, **kwargs), "baseline", PUBLIC_FALLBACK_WARNING)


def make_meta(outcome: GatewayOutcome, as_of: date) -> Meta:
    return Meta(source=outcome.source, as_of=as_of, generated_at=datetime.now(timezone.utc),
                warning=outcome.warning)
