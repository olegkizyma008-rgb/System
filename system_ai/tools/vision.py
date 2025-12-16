import base64
import os
import tempfile
import subprocess
from typing import Any, Dict, Optional


def analyze_image_local(image_path: str, *, mode: str = "auto") -> Dict[str, Any]:
    """Best-effort local analysis. Uses dop_materials vision module if present; otherwise returns minimal info."""
    try:
        from dop_materials.super_rag_agent.vision_module import get_vision_module  # type: ignore

        vm = get_vision_module()
        return vm.analyze_screenshot(image_path, mode=mode)
    except Exception as e:
        return {"status": "error", "error": str(e), "image_path": image_path, "mode": mode}


def summarize_image_for_prompt(image_path: str) -> str:
    """Return compact textual observation for LLM prompts."""
    try:
        analysis = analyze_image_local(image_path, mode="auto")
        if analysis.get("status") != "success":
            return f"[VISION] error: {analysis.get('error', 'unknown')}"
        combined = str(analysis.get("combined_description") or "").strip()
        if combined:
            return f"[VISION]\n{combined}"
        return "[VISION] (no combined_description)"
    except Exception as e:
        return f"[VISION] error: {e}"


def load_image_b64(image_path: str) -> Optional[str]:
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def load_image_png_b64(image_path: str) -> Optional[str]:
    """Return a PNG base64 payload.

    Copilot Vision is picky about accepted media types; we normalize to PNG.
    """
    if not image_path or not os.path.exists(image_path):
        return None

    try:
        from PIL import Image  # type: ignore

        img = Image.open(image_path)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            img.save(tmp_path, format="PNG")
            return load_image_b64(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception:
        pass

    # macOS fallback: sips conversion
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            subprocess.run(["sips", "-s", "format", "png", image_path, "--out", tmp_path], capture_output=True)
            if os.path.exists(tmp_path):
                return load_image_b64(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception:
        return None

    return None

def analyze_with_copilot(image_path: str, prompt: str = "Describe the user interface state in detail.") -> Dict[str, Any]:
    """
    Uses CopilotLLM (GPT-4-Vision) to analyze a local image file.
    """
    if not image_path or not os.path.exists(image_path):
        return {"status": "error", "error": f"Image not found: {image_path}"}
        
    try:
        from providers.copilot import CopilotLLM
        from langchain_core.messages import HumanMessage
        
        # Initialize specialized Vision LLM
        # We assume CopilotLLM handles the image_url payload format for its API
        llm = CopilotLLM(vision_model_name="gpt-4.1") 
        
        # Encode image
        b64 = load_image_png_b64(image_path)
        if not b64:
             return {"status": "error", "error": "Failed to encode image"}
             
        # Construct Message
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
            ]
        )
        
        # Invoke
        response = llm.invoke([message])
        return {"status": "success", "analysis": response.content}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


def ocr_region(x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    """Best-effort OCR for a screen region.

    Implementation: capture region -> send to Copilot Vision with an extraction prompt.
    This avoids hardcoding and works across apps, but requires vision model + Screen Recording permission.
    """
    try:
        from system_ai.tools.screenshot import capture_screen_region

        snap = capture_screen_region(x=x, y=y, width=width, height=height)
        if snap.get("status") != "success":
            return {"status": "error", **snap}

        image_path = str(snap.get("path") or "")
        analysis = analyze_with_copilot(
            image_path,
            prompt=(
                "Extract ALL visible text from this screenshot region. "
                "Return ONLY the extracted text (no commentary), keep line breaks." 
            ),
        )
        if analysis.get("status") != "success":
            return {"status": "error", "error": analysis.get("error"), "image_path": image_path}
        text = str(analysis.get("analysis") or "").strip()
        return {"status": "success", "text": text, "image_path": image_path}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def find_image_on_screen(template_path: str, tolerance: float = 0.9) -> Dict[str, Any]:
    """Find an image template on the primary screen using OpenCV template matching."""
    try:
        template_path_s = str(template_path or "").strip()
        if not template_path_s:
            return {"tool": "find_image_on_screen", "status": "error", "error": "template_path is required"}
        if not os.path.exists(template_path_s):
            return {
                "tool": "find_image_on_screen",
                "status": "error",
                "error": f"Template not found: {template_path_s}",
            }

        tol = float(tolerance)
        if tol <= 0.0 or tol > 1.0:
            return {
                "tool": "find_image_on_screen",
                "status": "error",
                "error": "tolerance must be within (0.0, 1.0]",
            }

        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            import mss  # type: ignore
        except ImportError as e:
            missing = str(e)
            return {
                "tool": "find_image_on_screen",
                "status": "error",
                "error_type": "missing_dependency",
                "error": f"Missing dependency: {missing}",
            }

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)

        screen = np.array(sct_img)
        if screen is None or screen.size == 0:
            return {"tool": "find_image_on_screen", "status": "error", "error": "Failed to capture screen"}

        if len(screen.shape) == 3 and screen.shape[2] == 4:
            screen_bgr = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
        else:
            screen_bgr = screen

        template = cv2.imread(template_path_s, cv2.IMREAD_UNCHANGED)
        if template is None or template.size == 0:
            return {
                "tool": "find_image_on_screen",
                "status": "error",
                "error": f"Failed to load template: {template_path_s}",
            }

        if len(template.shape) == 3 and template.shape[2] == 4:
            template_bgr = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        else:
            template_bgr = template

        th, tw = template_bgr.shape[:2]
        sh, sw = screen_bgr.shape[:2]
        if th <= 0 or tw <= 0:
            return {"tool": "find_image_on_screen", "status": "error", "error": "Invalid template size"}
        if th > sh or tw > sw:
            return {
                "tool": "find_image_on_screen",
                "status": "success",
                "found": False,
                "confidence": 0.0,
                "reason": "template_larger_than_screen",
            }

        result = cv2.matchTemplate(screen_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
        confidence = float(max_val)

        if confidence >= tol:
            x_center = int(max_loc[0] + (tw // 2))
            y_center = int(max_loc[1] + (th // 2))
            return {
                "tool": "find_image_on_screen",
                "status": "success",
                "found": True,
                "x": x_center,
                "y": y_center,
                "confidence": confidence,
                "match": {"x": int(max_loc[0]), "y": int(max_loc[1]), "width": int(tw), "height": int(th)},
            }

        return {
            "tool": "find_image_on_screen",
            "status": "success",
            "found": False,
            "confidence": confidence,
        }
    except Exception as e:
        err_str = str(e).lower()
        if "screen recording" in err_str or "access" in err_str:
            return {
                "tool": "find_image_on_screen",
                "status": "error",
                "error_type": "permission_required",
                "permission": "screen_recording",
                "error": "Permission denied. Please allow Screen Recording in System Settings.",
            }
        return {"tool": "find_image_on_screen", "status": "error", "error": str(e)}


def compare_images(path1: str, path2: str, prompt: str = None) -> Dict[str, Any]:
    """
    Compare two images (before/after) using GPT-4o-vision.
    
    Args:
        path1: Path to first image (before)
        path2: Path to second image (after)
        prompt: Custom comparison prompt (optional)
    
    Returns:
        Dict with comparison analysis
    """
    if not path1 or not os.path.exists(path1):
        return {"status": "error", "error": f"Image not found: {path1}"}
    if not path2 or not os.path.exists(path2):
        return {"status": "error", "error": f"Image not found: {path2}"}
    
    try:
        from providers.copilot import CopilotLLM
        from langchain_core.messages import HumanMessage
        
        # Initialize Vision LLM
        llm = CopilotLLM(vision_model_name="gpt-4.1")
        
        # Encode both images
        b64_1 = load_image_png_b64(path1)
        b64_2 = load_image_png_b64(path2)
        
        if not b64_1:
            return {"status": "error", "error": f"Failed to encode image: {path1}"}
        if not b64_2:
            return {"status": "error", "error": f"Failed to encode image: {path2}"}
        
        # Default prompt if not provided
        if not prompt:
            prompt = "Compare these two images (before and after). Describe all differences in detail. Are they as expected? List specific changes."
        
        # Construct message with both images
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_1}"},
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64_2}"},
                },
            ]
        )
        
        # Invoke vision model
        response = llm.invoke([message])
        analysis = response.content
        
        return {
            "status": "success",
            "analysis": analysis,
            "image1": path1,
            "image2": path2,
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
