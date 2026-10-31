"""
Core econometric module for extracting Fed funds implied rates and market
probabilities from 30-Day Federal Funds Futures (ZQ), based on methodology.pdf.
"""


def extract_post_meeting_rate(r_avg: float, r_pre: float, n_m: int, m_m: int) -> float:
    """
    Section 4.3 (Eq. 7): Expected post-meeting policy rate for a single month.
    
    Decomposes the contract average rate (r_avg) into the pre-meeting realized/expected
    segment (days 1 to m_m) and the post-meeting expected segment (remaining n_m - m_m days).

    Parameters:
    - r_avg: Monthly average rate implied by the future contract price (100 - P_m).
    - r_pre: Effective policy rate prevailing before the meeting (e.g., current EFFR).
    - n_m:   Total number of calendar days in month m.
    - m_m:   Calendar day of the FOMC policy decision announcement.

    Returns:
    - float: Expected post-meeting effective Federal Funds rate (R_post,m).
    """
    numerator = (n_m * r_avg) - (m_m * r_pre)
    denominator = n_m - m_m
    r_post = numerator / denominator
    return r_post


def resolve_post_meeting_rate(
    next_month_has_meeting: bool,
    r_avg: float,
    r_pre: float,
    n_m: int,
    m_m: int,
    r_avg_next: float | None = None,
    threshold_l: int = 7,
) -> float:
    """
    Resolves the post-meeting policy rate according to methodology Section 5.2.
    Applies the Next-Month Rule (Eq. 11) when days_remaining < threshold_l and
    no meeting occurs in month m+1. Gracefully falls back to Eq. 7 at the boundary.
    """
    days_remaining = n_m - m_m

    # Case 1: Sufficient remaining days in the month -> standard own-month estimator (Eq. 7)
    if days_remaining >= threshold_l:
        return extract_post_meeting_rate(r_avg=r_avg, r_pre=r_pre, n_m=n_m, m_m=m_m)

    # Case 2: Late-month meeting and subsequent month is an anchor (no meeting)
    if days_remaining < threshold_l and not next_month_has_meeting:
        if r_avg_next is not None:
            return r_avg_next
        # Boundary fallback: if at the end of the available curve, fall back to Eq. 7
        return extract_post_meeting_rate(r_avg=r_avg, r_pre=r_pre, n_m=n_m, m_m=m_m)

    # Case 3: Late-month meeting but subsequent month also has a meeting -> Eq. 7
    return extract_post_meeting_rate(r_avg=r_avg, r_pre=r_pre, n_m=n_m, m_m=m_m)


def extract_meeting_probabilities(r_post: float, r_pre: float, step: float = 0.25):
    """
    Section 5.1 (Eq. 14-17): Decomposition into a two-point discrete probability distribution.
    
    Translates the expected continuous rate change (r_post - r_pre) onto the two nearest
    admissible policy steps (lower_step and upper_step) separated by standard increments (step).

    Parameters:
    - r_post: Expected post-meeting policy rate.
    - r_pre:  Pre-meeting policy rate.
    - step:   Policy step size in percentage points (default = 0.25).

    Returns:
    - tuple: (h_m, lower_step, p_low, upper_step, p_high)
      - h_m:        Expected move normalized in step units ((r_post - r_pre) / step).
      - lower_step: Base rate adjustment in percentage points (s_m * k_m * step).
      - p_low:      Probability assigned to the base step (1.0 - alpha_m).
      - upper_step: Incremental rate adjustment (s_m * (k_m + 1) * step).
      - p_high:     Probability assigned to the incremental step (alpha_m).
    """
    h_m = (r_post - r_pre) / step

    # Direction of the expected policy move (+1 for hike, -1 for cut)
    if h_m >= 0:
        s_m = +1
    else:
        s_m = -1

    abs_h = abs(h_m)
    k_m = int(abs_h)           # Integer step count (characteristic)
    alpha_m = abs_h - k_m      # Fractional part (mantissa), mapped directly to probability

    # Admissible policy steps
    lower_step = s_m * k_m * step
    upper_step = s_m * (k_m + 1) * step

    # Two-point distribution probabilities (Eq. 17)
    p_low = 1.0 - alpha_m
    p_high = alpha_m

    return h_m, lower_step, p_low, upper_step, p_high


def convolve_meeting_step(
    current_dist: dict[float, float],
    lower_step: float,
    p_low: float,
    upper_step: float,
    p_high: float,
) -> dict[float, float]:
    """
    Section 5.3 (Eq. 23): Cumulative discrete convolution across consecutive FOMC meetings.
    
    Combines the probability distribution inherited from prior meetings (current_dist)
    with the discrete two-point distribution of the current meeting (q_j).

    Parameters:
    - current_dist: Prior cumulative probability state {cumulative_change: probability}.
    - lower_step:   Lower step adjustment of the incoming meeting.
    - p_low:        Probability of the lower step.
    - upper_step:   Upper step adjustment of the incoming meeting.
    - p_high:       Probability of the upper step.

    Returns:
    - dict[float, float]: Updated cumulative distribution {total_cumulative_change: joint_probability}.
    """
    new_dist = {}

    for old_rate, old_prob in current_dist.items():
        # Lower branch impact (joint probability: old_prob * p_low)
        rate_low = round(old_rate + lower_step, 4)
        prob_low = old_prob * p_low
        new_dist[rate_low] = new_dist.get(rate_low, 0.0) + prob_low

        # Upper branch impact (joint probability: old_prob * p_high)
        rate_high = round(old_rate + upper_step, 4)
        prob_high = old_prob * p_high
        new_dist[rate_high] = new_dist.get(rate_high, 0.0) + prob_high

    return new_dist