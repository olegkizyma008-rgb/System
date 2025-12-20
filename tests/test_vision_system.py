import os
import cv2
import numpy as np
import pytest
from system_ai.tools.vision import DifferentialVisionAnalyzer

def test_differential_vision_analyzer_init():
    analyzer = DifferentialVisionAnalyzer()
    assert analyzer is not None
    # Check for core attributes
    assert hasattr(analyzer, 'similarity_threshold')
    assert hasattr(analyzer, 'previous_frame')

def test_diff_analysis_logic(tmp_path):
    analyzer = DifferentialVisionAnalyzer()
    
    # Create two dummy images
    img1_path = str(tmp_path / "img1.png")
    img2_path = str(tmp_path / "img2.png")
    
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img2, (10, 10), (50, 50), (255, 255, 255), -1)
    
    cv2.imwrite(img1_path, img1)
    cv2.imwrite(img2_path, img2)
    
    # Test file reading and comparison logic
    result = analyzer.analyze_frame(img1_path, img2_path)
    assert result["status"] == "success"
    assert "diff" in result
    assert "ocr" in result

def test_vision_context_manager():
    from core.vision_context import VisionContextManager
    manager = VisionContextManager(max_history=2)
    
    manager.update_context({
        "timestamp": "2025-01-01T00:00:00",
        "diff": {"significant_change": True, "change_score": 0.5, "change_summary": "Buttons moving"},
        "ocr": {"status": "success", "full_text": "Login screen detected"},
        "context": "Login screen detected"
    })
    
    assert len(manager.history) == 1
    assert "Text detected: 'Login screen detected...'" in manager.current_context
    
    manager.update_context({
        "timestamp": "2025-01-01T00:00:01",
        "diff": {"significant_change": False},
        "ocr": {"status": "success", "full_text": "Success message shown"},
        "context": "Success message shown"
    })
    
    assert len(manager.history) == 2
    
    # Reaching limit
    manager.update_context({
        "timestamp": "2025-01-01T00:00:02",
        "diff": {"significant_change": True},
        "ocr": {"status": "success", "full_text": "Home page"},
        "context": "Home page"
    })
    
    assert len(manager.history) == 2
    assert "Success message shown" in manager.history[0]["data"]["context"]
