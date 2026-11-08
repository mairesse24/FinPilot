import importlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Literal

from app.schemas.common import Meta, ForecastReliability, Notice

log = logging.getLogger(__name__)
PUBLIC_FALLBACK_WARNING = "Some insights are temporarily unavailable. Showing a backup estimate."


@dataclass
class GatewayOutcome:
    value: Any
    source: Literal["model", "baseline"]
    warning: str | None = None
    forecast_reliability: ForecastReliability | None = None
    notices: list[Notice] | None = None


class Gateway:
    def __init__(self, mode: str = "auto", package: str = "intelligence"):
        self.mode = mode
        self.package = package

    def run(self, module: str, func: str, baseline: Callable, *args,
            expect: type | None = None, **kwargs) -> GatewayOutcome:
        if self.mode == "baseline":
            value = baseline(*args, **kwargs)
            return self._outcome(value,'baseline')
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
            value = baseline(*args, **kwargs)
            return self._outcome(value,'baseline')
        try:
            value = fn(*args, **kwargs)
        except Exception as exc:
            return self._fallback(baseline, args, kwargs, f"{name}.{func} failed ({type(exc).__name__})")
        if expect is not None and not isinstance(value, expect):
            return self._fallback(baseline, args, kwargs,
                                  f"{name}.{func} returned {type(value).__name__}, "
                                  f"expected {expect.__name__}")
        # A typed intelligence adapter can select a warned baseline fallback.
        # Preserve that provenance instead of relabeling every result as a model.
        meta = getattr(value, "meta", None)
        return self._outcome(value,getattr(meta,'source','model'))

    @staticmethod
    def _outcome(value,source):
        meta=getattr(value,'meta',None)
        return GatewayOutcome(value,source,getattr(meta,'warning',None),
                              getattr(meta,'forecast_reliability',None),getattr(meta,'notices',None))

    @staticmethod
    def _fallback(baseline, args, kwargs, warning: str) -> GatewayOutcome:
        log.warning(warning)
        value = baseline(*args, **kwargs)
        out=Gateway._outcome(value,'baseline')
        out.warning=PUBLIC_FALLBACK_WARNING
        from app.services.notices import merge_notices
        out.notices=merge_notices(out.notices or [],[Notice(code='calculation_fallback',context='analysis',category='critical',
            message=PUBLIC_FALLBACK_WARNING,technical_detail='An internal calculation provider failed; sensitive details were suppressed.')])
        return out


def make_meta(outcome: GatewayOutcome, as_of: date) -> Meta:
    from app.services.notices import merge_notices,notices_for
    return Meta(source=outcome.source, as_of=as_of, generated_at=datetime.now(timezone.utc),
                warning=outcome.warning,forecast_reliability=outcome.forecast_reliability,
                notices=merge_notices(outcome.notices or [],notices_for([outcome.warning],'analysis')))
