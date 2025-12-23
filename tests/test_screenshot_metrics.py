from PIL import Image

import system_ai.tools.screenshot as ss


def test_metrics_increment_on_success_and_failure(monkeypatch, tmp_path):
    # Reset metrics
    ss.METRICS["screenshot_total"] = 0
    ss.METRICS["screenshot_success"] = 0
    ss.METRICS["screenshot_failure"] = 0

    # Monkeypatch _capture_with_mss to return an image
    img = Image.new("RGB", (10, 10))

    def fake_capture_with_mss(region):
        return img, None

    monkeypatch.setattr(ss, "_capture_with_mss", fake_capture_with_mss)

    # Monkeypatch VisionDiffManager.process_screenshot to avoid filesystem writes
    monkeypatch.setattr(ss.VisionDiffManager, "process_screenshot", lambda self, im, fid: {"path": "/tmp/x.jpg", "mode": "initial", "bbox": None})

    res = ss.take_screenshot()
    assert res["status"] == "success"
    metrics = ss.get_metrics()
    assert metrics["screenshot_total"] == 1
    assert metrics["screenshot_success"] == 1
    assert metrics["screenshot_failure"] == 0

    # Now simulate failure via fallback
    def fake_capture_with_mss_fail(region):
        return None, "mss error"

    def fake_fallback(app_name, window_title, mss_error, manager, focus_id):
        return {"tool": "take_screenshot", "status": "error", "error": "simulated", "traceback": "tb"}

    monkeypatch.setattr(ss, "_capture_with_mss", fake_capture_with_mss_fail)
    monkeypatch.setattr(ss, "_capture_with_fallback", fake_fallback)

    res2 = ss.take_screenshot()
    assert res2["status"] == "error"
    metrics = ss.get_metrics()
    assert metrics["screenshot_total"] == 2
    assert metrics["screenshot_failure"] == 1
