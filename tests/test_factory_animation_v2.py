import unittest

from factory_animation_v2 import Bottle, classify_line_state, compute_layout


class FactoryAnimationV2Tests(unittest.TestCase):
    def test_compute_layout_returns_expected_regions(self):
        layout = compute_layout(1400, 820)
        self.assertGreaterEqual(layout["left_w"], 220)
        self.assertGreaterEqual(layout["right_w"], 230)
        self.assertGreaterEqual(layout["mid_w"], 500)
        self.assertGreaterEqual(layout["conv_y"], 130)

    def test_classify_line_state_flags_overheat_and_defect_risk(self):
        self.assertEqual(classify_line_state(46.0, 0.14, 45), "DEFECT STOP")
        self.assertEqual(classify_line_state(49.5, 0.02, 10), "OVERHEAT STOP")
        self.assertEqual(classify_line_state(35.0, 0.03, 10), "RUNNING")

    def test_bottle_inspection_detects_minor_defects(self):
        bottle = Bottle(100, 400)
        bottle.metrics = {
            "shape": 0.90,
            "crack": 0.03,
            "scale": 0.96,
            "color_off": 13.0,
            "label": False,
        }
        issues = bottle.inspect()
        self.assertIn("Shape distortion", issues)
        self.assertIn("Crack detected", issues)
        self.assertIn("Colour variance", issues)
        self.assertIn("Size error", issues)
        self.assertIn("Label missing", issues)


if __name__ == "__main__":
    unittest.main()
