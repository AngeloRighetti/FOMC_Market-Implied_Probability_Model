"""
Orchestration module for FOMC Forward Chaining and discrete convolution.
Implements the sequential timeline across all calendar months (Section 5.2).
"""

from typing import Any
from extraction import (
    resolve_post_meeting_rate,
    extract_meeting_probabilities,
    convolve_meeting_step,
)


def run_forward_chain(
    calendar: list[dict[str, Any]],
    futures_rates: dict[tuple[int, int], float],
    initial_rate: float,
) -> list[dict[str, Any]]:
    """
    Executes sequential forward chaining across all active calendar months.
    Propagates rates and applies discrete convolution to track cumulative probabilities.
    """
    results: list[dict[str, Any]] = []
    current_dist: dict[float, float] = {0.0: 1.0}
    r_pre: float = initial_rate

    for idx, month_data in enumerate(calendar):
        y = month_data["year"]
        m = month_data["month"]
        n_m = month_data["days_in_month"]
        m_m = month_data["decision_day"]

        key = (y, m)
        if key not in futures_rates:
            continue

        r_avg = futures_rates[key]

        # Lookahead for Next-Month Rule
        if idx + 1 < len(calendar):
            next_month = calendar[idx + 1]
            next_has_meeting = next_month["decision_day"] is not None
            r_avg_next = futures_rates.get((next_month["year"], next_month["month"]))
        else:
            next_has_meeting = False
            r_avg_next = None

        if m_m is not None:
            # 1. Post-meeting expected rate
            r_post = resolve_post_meeting_rate(
                next_month_has_meeting=next_has_meeting,
                r_avg=r_avg,
                r_pre=r_pre,
                n_m=n_m,
                m_m=m_m,
                r_avg_next=r_avg_next,
            )

            # 2. Probability decomposition
            h_m, lower_step, p_low, upper_step, p_high = extract_meeting_probabilities(
                r_post=r_post,
                r_pre=r_pre,
            )

            # 3. Discrete convolution
            current_dist = convolve_meeting_step(
                current_dist=current_dist,
                lower_step=lower_step,
                p_low=p_low,
                upper_step=upper_step,
                p_high=p_high,
            )

            # 4. Save meeting record
            results.append({
                "year": y,
                "month": m,
                "decision_day": m_m,
                "r_pre": round(r_pre, 4),
                "r_post": round(r_post, 4),
                "expected_change": round(r_post - r_pre, 4),
                "h_m": round(h_m, 4),
                "lower_step": lower_step,
                "p_low": round(p_low, 4),
                "upper_step": upper_step,
                "p_high": round(p_high, 4),
                "cumulative_dist": current_dist.copy(),
            })

            # 5. Forward state update
            r_pre = r_post
        else:
            # Anchor month
            r_pre = r_avg

    return results