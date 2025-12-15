import builtins


def test_find_image_on_screen_requires_template_path():
    from system_ai.tools.vision import find_image_on_screen

    out = find_image_on_screen("", 0.9)
    assert out["status"] == "error"


def test_find_image_on_screen_missing_template_returns_error(tmp_path):
    from system_ai.tools.vision import find_image_on_screen

    missing = tmp_path / "nope.png"
    out = find_image_on_screen(str(missing), 0.9)
    assert out["status"] == "error"
    assert "Template not found" in str(out.get("error"))


def test_find_image_on_screen_invalid_tolerance_is_rejected(tmp_path):
    from system_ai.tools.vision import find_image_on_screen

    existing = tmp_path / "template.png"
    existing.write_bytes(b"")
    out = find_image_on_screen(str(existing), 2.0)
    assert out["status"] == "error"
    assert "tolerance" in str(out.get("error", "")).lower()


def test_find_image_on_screen_missing_cv2_dependency(tmp_path, monkeypatch):
    from system_ai.tools.vision import find_image_on_screen

    existing = tmp_path / "template.png"
    existing.write_bytes(b"not_a_real_image")

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "cv2":
            raise ImportError("No module named cv2")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    out = find_image_on_screen(str(existing), 0.9)
    assert out["status"] == "error"
    assert out.get("error_type") == "missing_dependency"
