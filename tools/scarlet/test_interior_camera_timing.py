"""Mathematical regression tests; NOT actual Scarlet gameplay tests."""
import math
import unittest
from interior_camera_timing import effective_alpha, smooth, sample


class CameraInterpolationTest(unittest.TestCase):
    def test_one_30_hz_step_is_unchanged(self):
        for alpha in (0.001, 0.1, 0.5, 0.9, 0.999):
            self.assertAlmostEqual(effective_alpha(alpha, 1 / 30), alpha, places=12)

    def test_two_half_steps_equal_one_full_step(self):
        for alpha in (0.001, 0.1, 0.5, 0.9, 0.999):
            a60 = effective_alpha(alpha, 1 / 60)
            self.assertAlmostEqual(1 - (1-a60) ** 2, alpha, places=12)
            x = smooth(0.0, 10.0, alpha, 1 / 60)
            self.assertAlmostEqual(smooth(x, 10.0, alpha, 1 / 60), 10*alpha, places=12)

    def test_equal_wall_time(self):
        for alpha in (0.01, 0.2, 0.7):
            self.assertAlmostEqual(sample(alpha, 2.0, 30), sample(alpha, 2.0, 60), places=12)

    def test_variable_delta(self):
        alpha = 0.4
        x = 0.0
        for dt in (1/60, 1/120, 1/40, 1/24, 1/30):
            x = smooth(x, 2.0, alpha, dt)
        elapsed = 1/60 + 1/120 + 1/40 + 1/24 + 1/30
        self.assertAlmostEqual(x, smooth(0.0, 2.0, alpha, elapsed), places=12)

    def test_boundaries_and_invalid_input(self):
        self.assertEqual(effective_alpha(0.4, 0), 0)
        self.assertEqual(effective_alpha(0, 1/60), 0)
        self.assertEqual(effective_alpha(1, 1/60), 1)
        for a, dt in ((-0.1, 0.01), (1.1, 0.01), (math.nan, 0.01),
                      (0.5, -0.01), (0.5, math.inf)):
            with self.assertRaises(ValueError):
                effective_alpha(a, dt)


if __name__ == '__main__':
    unittest.main()
