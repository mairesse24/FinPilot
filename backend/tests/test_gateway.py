import sys
from datetime import date

import pytest

from app.services.gateway import Gateway, make_meta, PUBLIC_FALLBACK_WARNING


@pytest.fixture
def pkg(tmp_path, monkeypatch):
    root = tmp_path / "fakeintel"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "good.py").write_text("def f(x):\n    return 'real'\n")
    (root / "boom.py").write_text("def f(x):\n    raise RuntimeError('bad')\n")
    (root / "wrongtype.py").write_text("def f(x):\n    return 42\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    yield "fakeintel"
    for k in [k for k in sys.modules if k.startswith("fakeintel")]:
        del sys.modules[k]


base = lambda x: "base"


def test_uses_real_module_when_present(pkg):
    o = Gateway(package=pkg).run("good", "f", base, 1, expect=str)
    assert (o.value, o.source, o.warning) == ("real", "model", None)


def test_falls_back_when_module_missing_without_warning(pkg):
    o = Gateway(package=pkg).run("nope", "f", base, 1)
    assert (o.value, o.source, o.warning) == ("base", "baseline", None)


def test_falls_back_when_function_raises_with_warning(pkg):
    o = Gateway(package=pkg).run("boom", "f", base, 1)
    assert o.source == "baseline" and o.value == "base"
    assert o.warning == PUBLIC_FALLBACK_WARNING
    assert "bad" not in o.warning and "fakeintel" not in o.warning


def test_falls_back_on_wrong_return_type_with_warning(pkg):
    o = Gateway(package=pkg).run("wrongtype", "f", base, 1, expect=str)
    assert o.source == "baseline" and o.warning


def test_baseline_mode_ignores_real_module(pkg):
    o = Gateway("baseline", pkg).run("good", "f", base, 1)
    assert o.value == "base" and o.source == "baseline"


def test_make_meta():
    m = make_meta(Gateway("baseline").run("x", "f", base, 1), date(2026, 11, 7))
    assert m.source == "baseline" and m.is_prototype_estimate and m.warning is None


def test_internal_errors_do_not_escape_to_metadata_or_logs(caplog):
    class BrokenGateway(Gateway):
        pass
    def broken(*args):
        raise RuntimeError("private-token and database-host")
    import types
    import unittest.mock
    module = types.SimpleNamespace(chat=broken)
    with unittest.mock.patch("app.services.gateway.importlib.import_module", return_value=module):
        out = BrokenGateway().run("copilot", "chat", lambda: "safe response")
    meta = make_meta(out, date(2026, 11, 7))
    assert meta.warning == PUBLIC_FALLBACK_WARNING
    assert "private-token" not in caplog.text + meta.warning
    assert "database-host" not in caplog.text + meta.warning
    assert "RuntimeError" not in meta.warning and "copilot" not in meta.warning
