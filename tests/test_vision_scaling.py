import unittest
from unittest.mock import patch, MagicMock
import os
import json
import tempfile
from system_ai.tools.vision import DifferentialVisionAnalyzer
from PIL import Image

class TestVisionScaling(unittest.TestCase):
    def setUp(self):
        self.analyzer = DifferentialVisionAnalyzer()
        # Create a dummy image
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.image_path = os.path.join(self.tmp_dir.name, "test.png")
        img = Image.new('RGB', (100, 200), color = 'red')
        img.save(self.image_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_perform_ocr_analysis_scaling(self, mock_exists, mock_run):
        # Mock binary and paths
        mock_exists.return_value = True
        
        # Mock OCR output JSON
        ocr_data = {
            "texts": "Hello World",
            "observations": [
                {
                    "text": "Hello",
                    "confidence": 0.9,
                    "quad": {
                        "topLeft": {"x": 0.1, "y": 0.1},
                        "topRight": {"x": 0.5, "y": 0.1},
                        "bottomRight": {"x": 0.5, "y": 0.2},
                        "bottomLeft": {"x": 0.1, "y": 0.2}
                    }
                }
            ]
        }
        
        def side_effect(cmd, capture_output=True, check=False):
            # Extract output path from cmd
            output_dir = cmd[cmd.index("--output") + 1]
            json_path = os.path.join(output_dir, "test.json")
            with open(json_path, 'w') as f:
                json.dump(ocr_data, f)
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        result = self.analyzer._perform_ocr_analysis(self.image_path)
        
        self.assertEqual(result["status"], "success")
        region = result["regions"][0]
        # Image is 100x200. x=0.1 -> 10, y=0.1 -> 20
        self.assertEqual(region["bbox"][0], [10.0, 20.0]) # topLeft
        self.assertEqual(region["bbox"][2], [50.0, 40.0]) # bottomRight

if __name__ == '__main__':
    unittest.main()
