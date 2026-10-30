"""
Theoretical validation test suite based on methodology.pdf.
Verifies analytical properties: conservation of expectations,
boundary conditions, discrete decomposition, and convolution.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.append(str(SRC_DIR))

from extraction import (
    extract_post_meeting_rate,
    resolve_post_meeting_rate,
    extract_meeting_probabilities,
    convolve_meeting_step,
)

def test_extract_post_meeting_rate_conservation() -> None:
    """
    Validates Eq. 7: Day-weighted average must recover r_avg exactly.
    """
    r_pre = 4.00
    n_m = 30
    m_m = 10
    r_avg = 3.90

    r_post = extract_post_meeting_rate(r_avg=r_avg, r_pre=r_pre, n_m=n_m, m_m=m_m)

    # Verifica la conservazione della media ponderata
    reconstructed_avg = (m_m * r_pre + (n_m - m_m) * r_post) / n_m
    assert abs(reconstructed_avg - r_avg) < 1e-9, "Weighted average conservation failed"


def test_resolve_post_meeting_rate() -> None:
    """
    Validates Eq. 11: The post-meeting estimator must apply the Next-Month Rule
    when remaining days < threshold_l and the subsequent month has no meeting.
    """
    r_pre = 4.00
    n_m = 30
    m_m = 27  # days_remaining = 3 (< 7)
    r_avg = 3.90
    r_avg_next = 3.75
    threshold_l = 7
    next_month_has_meeting = False

    # 1. Test Case: Late-month meeting + Anchor month -> Eq. 11 applies
    r_post = resolve_post_meeting_rate(
        next_month_has_meeting=next_month_has_meeting,
        r_avg=r_avg,
        r_pre=r_pre,
        n_m=n_m,
        m_m=m_m,
        r_avg_next=r_avg_next,
        threshold_l=threshold_l,
    )

    assert r_post == r_avg_next, f"Expected {r_avg_next}, got {r_post}"

    # 2. Counter-Case: Late-month meeting BUT next month HAS a meeting -> Fallback to Eq. 7
    r_post_fallback = resolve_post_meeting_rate(
            next_month_has_meeting=True,
            r_avg=r_avg,
            r_pre=r_pre,
            n_m=n_m,
            m_m=m_m,
            r_avg_next=r_avg_next,
            threshold_l=threshold_l,
    )

    expected_fallback = ((n_m * r_avg) - (m_m * r_pre)) / (n_m - m_m)
    assert abs(r_post_fallback - expected_fallback) < 1e-9, "Fallback to Eq. 7 failed"


def test_extract_meeting_probabilities() -> None:
    """
    Validate Eq. 14-17: Decomposition into a two-point discrete probability distribution.
    """
    # 1. Exact integer multiple case (+100 bps move, exactly 4 steps)
    r_pre = 4.00
    r_post = 5.00
    step = 0.25
    h_m, lower_step, p_low, upper_step, p_high = extract_meeting_probabilities(r_post=r_post, r_pre=r_pre, step=step)

    assert abs(h_m - 4.00) < 1e-9, f"Expected h_m = 4.0, got {h_m}"
    assert abs(lower_step - 1.00) < 1e-9, f"Expected lower_step = 1.00, got {lower_step}"
    assert abs(upper_step - 1.25) < 1e-9, f"Expected upper_step = 0.00, got {upper_step}"
    assert abs(p_low - 1.0) < 1e-9, f"Expected p_low = 1.0, got {p_low}"
    assert abs(p_high - 0.0) < 1e-9, f"Expected p_high = 0.0, got {p_high}"

    # 2. Fractional move case (+10 bps move -> 40% probability of +25 bps, 60% probability of 0 bps)
    r_post_frac = 4.10
    h_m_f, lower_step_f, p_low_f, upper_step_f, p_high_f = extract_meeting_probabilities(r_post=r_post_frac, r_pre=r_pre, step=step)
    assert abs(h_m_f - 0.40) < 1e-9, f"Expected h_m_f = 0.40, got {h_m_f}"
    assert abs(lower_step_f - 0.00) < 1e-9, f"Expected lower_step_f = 0.00, got {lower_step_f}"
    assert abs(upper_step_f - 0.25) < 1e-9, f"Expected upper_step_f = 0.25, got {upper_step_f}"
    assert abs(p_low_f - 0.6) < 1e-9, f"Expected p_low_f = 0.6, got {p_low_f}"
    assert abs(p_high_f - 0.4) < 1e-9, f"Expected p_high_f = 0.4, got {p_high_f}"

    # 3. Conservation of expected value: E[delta_R] must equal r_post - r_pre
    expected_change = p_low_f * lower_step_f + p_high_f * upper_step_f
    actual_change = r_post_frac - r_pre
    assert (expected_change - actual_change) < 1e-9, "Expected value conservation failed"


    """
    Validate Eq. 23: Discrete convolution across sequential FOMC meetings.
    Ensures total probability conservation and exact branch recombination.
    """
    initial_dist = {0.0: 1.0}

    dist_meeting_1 = convolve_meeting_step(
        current_dist=initial_dist,
        lower_step=0.00,
        p_low=0.50,
        upper_step=-0.25,
        p_high=0.50,
    )

    assert len(dist_meeting_1) == 2, f"Expected 2 branches, got {len(dist_meeting_1)}"
    assert abs(dist_meeting_1[0.00] - 0.50) < 1e-9, "Meeting 1 hold probability mismatch"
    assert abs(dist_meeting_1[-0.25] - 0.50) < 1e-9, "Meeting 1 cut probability mismatch"
    assert abs(sum(dist_meeting_1.values()) - 1.0) < 1e-9, "Meeting 1 total probability != 1.0"

    dist_meeting_2 = convolve_meeting_step(
        current_dist=dist_meeting_1,
        lower_step=0.00,
        p_low=0.50,
        upper_step=-0.25,
        p_high=0.50,
    )

    assert len(dist_meeting_2) == 3, f"Expected 3 combined nodes, got {len(dist_meeting_2)}"
    assert abs(dist_meeting_2[0.00] - 0.25) < 1e-9, "Node 0.00% mismatch"
    assert abs(dist_meeting_2[-0.25] - 0.50) < 1e-9, "Node -0.25% mismatch"
    assert abs(dist_meeting_2[-0.50] - 0.25) < 1e-9, "Node -0.50% mismatch"

    total_prob = sum(dist_meeting_2.values())
    assert abs(total_prob - 1.0) < 1e-9, f"Total probability mismatch: {total_prob}"


def test_convolve_meeting_step() -> None:
    """
    Validate Eq. 23: Discrete convolution across sequential FOMC meetings.
    Ensures total probability conservation and exact branch recombination.
    """
    # 1. Base state: zero initial policy adjustment with 100% certainty
    initial_dist = {0.0: 1.0}

    # Meeting 1: 50% probability of hold (0.00), 50% probability of 25 bps cut (-0.25)
    dist_meeting_1 = convolve_meeting_step(
        current_dist=initial_dist,
        lower_step=0.00,
        p_low=0.50,
        upper_step=-0.25,
        p_high=0.50,
    )

    # Assert meeting 1 branches
    assert len(dist_meeting_1) == 2, f"Expected 2 branches, got {len(dist_meeting_1)}"
    assert abs(dist_meeting_1[0.00] - 0.50) < 1e-9, "Meeting 1 hold probability mismatch"
    assert abs(dist_meeting_1[-0.25] - 0.50) < 1e-9, "Meeting 1 cut probability mismatch"
    assert abs(sum(dist_meeting_1.values()) - 1.0) < 1e-9, "Meeting 1 total probability != 1.0"

    # Meeting 2: identical shock distribution (50% hold, 50% cut of -25 bps)
    dist_meeting_2 = convolve_meeting_step(
        current_dist=dist_meeting_1,
        lower_step=0.00,
        p_low=0.50,
        upper_step=-0.25,
        p_high=0.50,
    )

    # 2. Check recombined tree outcomes: 0 bps, -25 bps, -50 bps
    assert len(dist_meeting_2) == 3, f"Expected 3 combined nodes, got {len(dist_meeting_2)}"
    assert abs(dist_meeting_2[0.00] - 0.25) < 1e-9, "Node 0.00% (hold + hold) must equal 0.25"
    assert abs(dist_meeting_2[-0.25] - 0.50) < 1e-9, "Node -0.25% (cross-paths) must recombine to 0.50"
    assert abs(dist_meeting_2[-0.50] - 0.25) < 1e-9, "Node -0.50% (cut + cut) must equal 0.25"

    # 3. Total probability conservation check
    total_prob = sum(dist_meeting_2.values())
    assert abs(total_prob - 1.0) < 1e-9, f"Total probability after convolution must be 1.0, got {total_prob}"


if __name__ == "__main__":
    test_extract_post_meeting_rate_conservation()
    test_resolve_post_meeting_rate()
    test_extract_meeting_probabilities()
    test_convolve_meeting_step()
    print("All methodology tests passed successfully.")