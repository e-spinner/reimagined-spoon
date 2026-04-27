from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "reimagined-spoon"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_final_project.cv_boxes import detect_answer_region_from_pdf, export_detection_debug_images


class TestCVBoxDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pdf_path = Path(__file__).resolve().parents[1] / "Unit Tests" / "fixtures" / "MichaelSmithHW1.pdf"
        cls.debug_dir = Path(__file__).resolve().parents[0] / "output" / "cv_box_detection"
        cls.debug_paths = export_detection_debug_images(
            cls.pdf_path,
            cls.debug_dir,
            prefix="michael_smith_hw1",
        )

    def test_finds_filled_lower_right_marker_box(self) -> None:
        detection = detect_answer_region_from_pdf(self.pdf_path)

        self.assertGreater(detection.marker_fill_ratio, 0.08)

        page_anchor_x = detection.marker_box.x + detection.marker_box.w / 2.0
        page_anchor_y = detection.marker_box.y + detection.marker_box.h / 2.0
        self.assertGreater(page_anchor_x, 250)
        self.assertGreater(page_anchor_y, 250)

    def test_crops_answer_box_from_marker_match(self) -> None:
        detection = detect_answer_region_from_pdf(self.pdf_path)

        crop = detection.answer_crop
        self.assertIsInstance(crop, np.ndarray)
        self.assertGreater(crop.shape[0], 40)
        self.assertGreater(crop.shape[1], 80)

        ink_ratio = float(np.count_nonzero(crop < 200)) / float(crop.size)
        self.assertGreater(ink_ratio, 0.01)
        # Guard against regressions where a distant top-page rectangle is chosen.
        self.assertGreater(detection.answer_box.y, 1500)

    def test_writes_debug_images_for_human_review(self) -> None:
        self.assertTrue(self.debug_paths.overlay_path.exists())
        self.assertTrue(self.debug_paths.marker_crop_path.exists())
        self.assertTrue(self.debug_paths.answer_crop_path.exists())
        self.assertGreater(self.debug_paths.overlay_path.stat().st_size, 0)
        self.assertGreater(self.debug_paths.marker_crop_path.stat().st_size, 0)
        self.assertGreater(self.debug_paths.answer_crop_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
