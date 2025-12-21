import base64
import os
import tempfile
import subprocess
import hashlib
from typing import Any, Dict, Optional, List
from datetime import datetime
import numpy as np


def analyze_image_local(image_path: str, *, mode: str = "auto") -> Dict[str, Any]:
    """Best-effort local analysis. Uses super-rag vision module if present; otherwise returns minimal info."""
    try:
        from super_rag.vision_module import get_vision_module  # type: ignore

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


def load_image_png_b64(image_path: str, max_dimension: int = 1024) -> Optional[str]:
    """Return a PNG base64 payload, resized if needed to avoid payload limits.

    Copilot Vision is picky about accepted media types; we normalize to PNG.
    We also resize to max_dimension (default 1024px) to avoid HTTP 413 errors.
    """
    if not image_path or not os.path.exists(image_path):
        return None

    try:
        from PIL import Image  # type: ignore

        img = Image.open(image_path)
        
        # Resize if too large
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            ratio = min(max_dimension / width, max_dimension / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
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

    # macOS fallback: sips conversion (only checks format, not resize for now, 
    # but likely PIL is available in this env)
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            subprocess.run(["sips", "-s", "format", "png", image_path, "--out", tmp_path], capture_output=True)
            if os.path.exists(tmp_path):
                # Note: If PIL failed, we might still have a large image here. 
                # Ideally we should resize with sips too if needed: 
                # sips -Z 1024 ...
                subprocess.run(["sips", "-Z", str(max_dimension), tmp_path], capture_output=True)
                return load_image_b64(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception:
        return None

    return None

def analyze_with_copilot(image_path: str = None, prompt: str = "Describe the user interface state in detail.") -> Dict[str, Any]:
    """
    Uses CopilotLLM (GPT-4-Vision) to analyze a local image file.
    If image_path is none or doesn't exist, takes a fresh screenshot first.
    """
    if not image_path or not os.path.exists(image_path):
        from system_ai.tools.screenshot import take_screenshot
        res = take_screenshot()
        if res.get("status") != "success":
            return {"status": "error", "error": f"Image not found and failed to take screenshot: {res.get('error')}"}
        image_path = res.get("path")
        
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

class DifferentialVisionAnalyzer:
    """Core class for differential visual analysis with OCR and multi-monitor support.
    
    Enhanced features:
    - Multi-monitor screenshot capture
    - Diff image generation for visualization
    - Improved region detection with monitor indexing
    - Color and structure analysis
    """

    def __init__(self):
        self.previous_frame = None
        self.context_history = []
        self.similarity_threshold = float(os.getenv("VISION_SIMILARITY_THRESHOLD", "0.95"))
        self._ocr_engine = None
        self._monitor_count = 1
        self._last_diff_image_path: Optional[str] = None

    def _get_ocr_engine(self):
        """Lazy load OCR engine to avoid overhead if not used"""
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR
                # Initialize PaddleOCR with ukrainian and english support
                self._ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except ImportError:
                # Fallback to a dummy or logger if not installed
                self._ocr_engine = "unavailable"
        return self._ocr_engine

    def capture_all_monitors(self) -> Dict[str, Any]:
        """Capture screenshot from all monitors using native macOS APIs.
        
        Returns combined image path and monitor info.
        """
        try:
            # Try native macOS multi-monitor capture
            from Quartz import (
                CGGetActiveDisplayList, 
                CGDisplayBounds,
                CGWindowListCreateImage,
                CGRectMake,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )
            from Cocoa import NSBitmapImageRep, NSPNGFileType
            import Quartz
            
            # Get all displays
            max_displays = 16
            active_displays, num_displays = CGGetActiveDisplayList(max_displays, None, None)
            self._monitor_count = num_displays
            
            if num_displays == 0:
                return {"status": "error", "error": "No displays found"}
            
            # Calculate combined bounds
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = float('-inf'), float('-inf')
            
            for display_id in active_displays[:num_displays]:
                bounds = CGDisplayBounds(display_id)
                min_x = min(min_x, bounds.origin.x)
                min_y = min(min_y, bounds.origin.y)
                max_x = max(max_x, bounds.origin.x + bounds.size.width)
                max_y = max(max_y, bounds.origin.y + bounds.size.height)
            
            # Capture combined rect
            combined_rect = CGRectMake(min_x, min_y, max_x - min_x, max_y - min_y)
            image = CGWindowListCreateImage(
                combined_rect,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                0
            )
            
            if image is None:
                return {"status": "error", "error": "Failed to capture screen image"}
            
            # Save to file
            bitmap = NSBitmapImageRep.alloc().initWithCGImage_(image)
            png_data = bitmap.representationUsingType_properties_(NSPNGFileType, None)
            
            output_path = tempfile.mktemp(suffix=".png")
            png_data.writeToFile_atomically_(output_path, True)
            
            return {
                "status": "success",
                "path": output_path,
                "monitor_count": num_displays,
                "bounds": {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y}
            }
            
        except ImportError:
            # Fallback to mss for multi-monitor
            try:
                import mss
                
                with mss.mss() as sct:
                    # Monitor 0 is the combined view
                    self._monitor_count = len(sct.monitors) - 1
                    screenshot = sct.grab(sct.monitors[0])
                    
                    output_path = tempfile.mktemp(suffix=".png")
                    mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
                    
                    return {
                        "status": "success",
                        "path": output_path,
                        "monitor_count": self._monitor_count,
                        "bounds": sct.monitors[0]
                    }
            except Exception as e:
                return {"status": "error", "error": f"mss fallback failed: {e}"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def analyze_frame(self, image_path: str, reference_path: str = None, generate_diff_image: bool = False) -> dict:
        """
        Analyze frame with differential comparison, OCR, and optional diff image generation.
        
        Args:
            image_path: Path to current image
            reference_path: Optional path to reference image
            generate_diff_image: If True, creates a visualization of differences
        """
        try:
            import cv2
            
            # 1. Load current frame
            current_frame = cv2.imread(image_path)
            if current_frame is None:
                return {"status": "error", "error": f"Cannot load image at {image_path}"}

            # 2. Comparison reference
            ref_frame = None
            if reference_path:
                ref_frame = cv2.imread(reference_path)
            elif self.previous_frame is not None:
                ref_frame = self.previous_frame

            # 3. Calculate differences
            diff_result = {}
            if ref_frame is not None:
                diff_result = self._calculate_frame_diff(ref_frame, current_frame, generate_diff_image)
            else:
                diff_result = {
                    "global_change_percentage": 0,
                    "has_significant_changes": False,
                    "changed_regions": [],
                    "note": "No reference frame for comparison",
                    "monitor_count": self._monitor_count
                }

            # 4. Perform OCR
            ocr_results = self._perform_ocr_analysis(image_path)

            # 5. Store state
            self.previous_frame = current_frame

            # 6. Generate summary
            context_summary = self._generate_context_summary(diff_result, ocr_results)

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "diff": diff_result,
                "ocr": ocr_results,
                "context": context_summary
            }
            
            if generate_diff_image and self._last_diff_image_path:
                result["diff_image_path"] = self._last_diff_image_path

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _calculate_frame_diff(self, prev_frame, curr_frame, generate_image: bool = False) -> dict:
        """Calculate visual differences between frames using OpenCV."""
        import cv2
        
        # Ensure identical sizes
        if prev_frame.shape != curr_frame.shape:
             # Resize curr to prev for comparison if needed
             curr_frame_resized = cv2.resize(curr_frame, (prev_frame.shape[1], prev_frame.shape[0]))
        else:
             curr_frame_resized = curr_frame

        # Structural difference
        diff = cv2.absdiff(prev_frame, curr_frame_resized)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # Threshold to find significant changes
        _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
        
        non_zero = cv2.countNonZero(thresh)
        total_pixels = gray_diff.size
        change_percentage = (non_zero / total_pixels) * 100

        # Find changed regions
        contours_result = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Handle different OpenCV versions (returns 2 or 3 values)
        contours = contours_result[0] if len(contours_result) == 2 else contours_result[1]
        changed_regions = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:  # Ignore noise
                x, y, w, h = cv2.boundingRect(cnt)
                
                # Calculate which monitor this region belongs to
                monitor_idx = self._get_monitor_for_position(x, y)
                
                # Calculate color change intensity in region
                region_diff = diff[y:y+h, x:x+w]
                color_intensity = float(np.mean(region_diff)) if region_diff.size > 0 else 0
                
                changed_regions.append({
                    "area": float(area),
                    "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "monitor": monitor_idx,
                    "color_intensity": color_intensity
                })

        # Generate diff visualization image
        if generate_image and len(changed_regions) > 0:
            self._last_diff_image_path = self._generate_diff_image(curr_frame_resized, changed_regions)

        return {
            "global_change_percentage": float(change_percentage),
            "changed_regions": changed_regions,
            "has_significant_changes": change_percentage > (1.0 - self.similarity_threshold) * 100,
            "monitor_count": self._monitor_count
        }

    def _get_monitor_for_position(self, x: int, y: int) -> int:
        """Determine which monitor a position belongs to (simplified)."""
        # This is a simplified version - could be enhanced with actual monitor bounds
        # For now, divide screen width by monitor count
        if self._monitor_count <= 1:
            return 0
        # Assume horizontal arrangement, ~1920px per monitor
        return min(x // 1920, self._monitor_count - 1)

    def _generate_diff_image(self, frame, regions: List[Dict]) -> str:
        """Generate a visualization of changed regions."""
        import cv2
        
        output = frame.copy()
        
        for region in regions:
            bbox = region.get("bbox", {})
            x, y = bbox.get("x", 0), bbox.get("y", 0)
            w, h = bbox.get("width", 0), bbox.get("height", 0)
            
            # Color based on intensity
            intensity = region.get("color_intensity", 50)
            color = (0, int(min(255, intensity * 3)), 255)  # Orange to red gradient
            
            # Draw rectangle
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
            
            # Add label
            label = f"M{region.get('monitor', 0)} {int(region.get('area', 0))}px"
            cv2.putText(output, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Save
        output_path = tempfile.mktemp(suffix="_diff.png")
        cv2.imwrite(output_path, output)
        
        return output_path

    def _perform_ocr_analysis(self, image_path: str) -> dict:
        """Perform OCR using PaddleOCR if available, else fallback to Copilot analysis"""
        engine = self._get_ocr_engine()
        
        if engine == "unavailable":
            # Fallback to analyze_with_copilot for critical OCR if possible
            # or return empty result
            return {"status": "unavailable", "note": "PaddleOCR not installed"}
            
        try:
            result = engine.ocr(image_path, cls=True)
            text_regions = []
            
            if result and result[0]:
                for line in result[0]:
                    bbox = line[0]
                    text, conf = line[1]
                    text_regions.append({
                        "text": text,
                        "confidence": float(conf),
                        "bbox": bbox
                    })

            return {
                "status": "success",
                "regions": text_regions,
                "full_text": " ".join([r["text"] for r in text_regions])
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _generate_context_summary(self, diff_data: dict, ocr_data: dict) -> str:
        """Generate human-readable context summary"""
        summary = []
        
        if diff_data.get("has_significant_changes"):
            summary.append(f"Detected screen changes ({diff_data['global_change_percentage']:.1f}%)")
            if diff_data.get("monitor_count", 1) > 1:
                summary.append(f"across {diff_data['monitor_count']} monitors")
        else:
            summary.append("Screen remains mostly stable")

        if ocr_data.get("status") == "success" and ocr_data.get("full_text"):
            text = ocr_data["full_text"]
            if len(text) > 100:
                text = text[:97] + "..."
            summary.append(f"Visible text: {text}")

        return ". ".join(summary)


class EnhancedVisionTools:
    """Entry point for Trinity vision operations with enhanced capabilities."""

    _analyzer_instance = None

    @classmethod
    def get_analyzer(cls) -> DifferentialVisionAnalyzer:
        if cls._analyzer_instance is None:
            cls._analyzer_instance = DifferentialVisionAnalyzer()
        return cls._analyzer_instance

    @staticmethod
    def capture_and_analyze(
        image_path: str = None, 
        reference_path: str = None,
        generate_diff_image: bool = False,
        multi_monitor: bool = True,
        app_name: str = None,
        window_title: str = None
    ) -> dict:
        """Tool implementation for differential vision analysis.
        
        Args:
            image_path: Path to image to analyze (if None, captures screen)
            reference_path: Optional reference image for comparison
            generate_diff_image: Generate visualization of changes
            multi_monitor: Use multi-monitor capture (default True)
            app_name: Optional app name to capture specific window (e.g., "Safari", "Chrome")
            window_title: Optional window title substring to filter specific window
        """
        analyzer = EnhancedVisionTools.get_analyzer()
        
        # If no image path, take a screenshot
        if not image_path:
            # Smart capture based on context
            if app_name:
                # Capture specific app window
                from system_ai.tools.screenshot import take_screenshot
                snap = take_screenshot(app_name=app_name, window_title=window_title, activate=False)
            elif multi_monitor:
                snap = analyzer.capture_all_monitors()
            else:
                from system_ai.tools.screenshot import take_screenshot
                snap = take_screenshot()
            
            if snap.get("status") != "success":
                return snap
            image_path = snap.get("path")

        result = analyzer.analyze_frame(image_path, reference_path, generate_diff_image)
        
        # Add capture context to result
        result["capture_context"] = {
            "method": "app_window" if app_name else ("multi_monitor" if multi_monitor else "primary"),
            "app_name": app_name,
            "window_title": window_title
        }
        
        return result

    @staticmethod
    def analyze_with_context(image_path: str, context_manager: Any) -> dict:
        """Analyze image and update the shared vision context"""
        result = EnhancedVisionTools.capture_and_analyze(image_path)
        if result.get("status") == "success":
            context_manager.update_context(result)
        return result

    @staticmethod
    def get_multi_monitor_screenshot() -> dict:
        """Capture screenshot from all monitors."""
        analyzer = EnhancedVisionTools.get_analyzer()
        return analyzer.capture_all_monitors()

    @staticmethod
    def analyze_with_diff_visualization(reference_path: str = None) -> dict:
        """Analyze current screen with diff visualization."""
        return EnhancedVisionTools.capture_and_analyze(
            image_path=None,
            reference_path=reference_path,
            generate_diff_image=True,
            multi_monitor=True
        )

