import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtWidgets import QApplication

from watermark_app import WatermarkApp


class WatermarkAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])
        cls.window = WatermarkApp()

    def setUp(self):
        self.background = np.full((8, 10, 3), 100, dtype=np.uint8)

    def test_manual_mode_respects_png_transparency_and_global_opacity(self):
        watermark = np.zeros((2, 2, 4), dtype=np.uint8)
        watermark[:, :, :3] = (200, 200, 200)
        watermark[:, :, 3] = ((255, 0), (255, 0))

        result = self.window.apply_watermark_manual(
            self.background, watermark, "Левый верх", 0.5, 0, 0)

        self.assertTrue(np.all(result[0, 0] == 150))
        self.assertTrue(np.all(result[0, 1] == 100))

    def test_opencv_mode_respects_png_transparency_and_global_opacity(self):
        watermark = np.zeros((2, 2, 4), dtype=np.uint8)
        watermark[:, :, :3] = (200, 200, 200)
        watermark[:, :, 3] = ((255, 0), (255, 0))

        result = self.window.apply_watermark_lib(
            self.background, watermark, "Левый верх", 0.5, 0, 0)

        self.assertTrue(np.all(result[0, 0] == 150))
        self.assertTrue(np.all(result[0, 1] == 100))

    def test_corner_positions_and_custom_coordinates(self):
        watermark = np.full((2, 2, 3), 220, dtype=np.uint8)
        cases = (("Левый верх", 0, 0), ("Правый верх", 8, 0),
                 ("Левый низ", 0, 6), ("Правый низ", 8, 6),
                 ("Центр", 4, 3), ("Произвольно", 3, 2))

        for position, expected_x, expected_y in cases:
            with self.subTest(position=position):
                result = self.window.apply_watermark_manual(
                    self.background, watermark, position, 1.0, 3, 2)
                self.assertTrue(np.all(result[expected_y, expected_x] == 220))

    def test_watermark_larger_than_background_is_resized_to_fit(self):
        background = np.full((4, 6, 3), 100, dtype=np.uint8)
        watermark = np.full((8, 16, 3), 200, dtype=np.uint8)

        result = self.window.apply_watermark_manual(
            background, watermark, "Левый верх", 1.0, 0, 0)

        self.assertEqual(result.shape, background.shape)
        self.assertTrue(np.all(result[:3, :, :] == 200))
        self.assertTrue(np.all(result[3, :, :] == 100))

    def test_window_can_process_loaded_images(self):
        self.window.background = self.background
        self.window.watermark = np.full((2, 2, 3), 200, dtype=np.uint8)

        self.window.process_watermark()

        self.assertEqual(self.window.result.shape, self.background.shape)


if __name__ == "__main__":
    unittest.main()
