"""
Unit tests for the FOMC Market-Implied Probability Model.
Tests the core mathematical functions isolated from the main script.
Reference: methodology.pdf
"""

import unittest
from main import (
    extract_post_meeting_rate,
    resolve_post_meeting_rate,
    extract_meeting_probabilities,
    convolve_meeting_step
)

class TestFOMCMathCore(unittest.TestCase):

    def test_extract_post_meeting_rate(self):
        """Tests Eq. 7: Base estimator for the current month."""
        # Example: Meeting on the 15th of a 31-day month.
        # r_avg = 4.0%, r_pre = 4.1%
        # Calculation: (31 * 4.0 - 15 * 4.1) / (31 - 15) = 3.90625
        r_post = extract_post_meeting_rate(r_avg=4.0, r_pre=4.1, n_m=31, m_m=15)
        self.assertAlmostEqual(r_post, 3.90625, places=5)

    def test_resolve_post_meeting_rate_late_month(self):
        """Tests Eq. 11: Next-Month Rule for late-month meetings."""
        # Meeting on the 27th (4 days remaining, < 7). No meeting next month.
        # It must return r_avg_next directly to avoid end-of-month volatility.
        r_post = resolve_post_meeting_rate(
            next_month_has_meeting=False,
            r_avg=4.0, r_pre=4.1, n_m=31, m_m=27,
            r_avg_next=3.95
        )
        self.assertEqual(r_post, 3.95)

    def test_extract_meeting_probabilities(self):
        """Tests Eq. 14-17: Probability decomposition into 25 bps steps."""
        # Using real data from the December 2026 meeting:
        # r_pre = 3.880%, r_post = 4.063% (delta = +18.3 bps)
        # 18.3 / 25.0 = 0.732 -> 73.2% probability for the upper step.
        h_m, l_step, p_low, u_step, p_high = extract_meeting_probabilities(r_post=4.063, r_pre=3.880)
        
        self.assertAlmostEqual(l_step, 0.0, places=4)
        self.assertAlmostEqual(u_step, 0.25, places=4)
        self.assertAlmostEqual(p_high, 0.732, places=4)
        self.assertAlmostEqual(p_low, 0.268, places=4)

    def test_convolve_meeting_step(self):
        """Tests Eq. 23: Discrete convolution and cumulative distribution update."""
        # Initial state: 100% certainty (1.0) at the 0.0 change level.
        initial_dist = {0.0: 1.0}
        
        # Apply the 73.2% probability of a 25 bps hike.
        new_dist = convolve_meeting_step(
            current_dist=initial_dist,
            lower_step=0.0, p_low=0.268,
            upper_step=0.25, p_high=0.732
        )
        
        # Verify the nodes split correctly.
        self.assertIn(0.0, new_dist)
        self.assertIn(0.25, new_dist)
        self.assertAlmostEqual(new_dist[0.0], 0.268, places=4)
        self.assertAlmostEqual(new_dist[0.25], 0.732, places=4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
    