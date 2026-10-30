"""
Test suite for Forward Chaining and multi-meeting probability convolution.
"""

import sys
from pathlib import Path

# Append src directory to Python path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.append(str(SRC_DIR))

from calendar_data import CALENDAR_2026
from chain import run_forward_chain


def test_chain_execution() -> None:
    """
    Validates forward chaining execution across all FOMC meetings in 2026.
    Ensures conditional probabilities and cumulative distributions sum to 1.0.
    """
    starting_effr = 3.88

    # Simulated forward curve (R_avg = 100 - P_m)
    sample_futures_rates = {
        1: 3.85,   # January (Decision: Jan 28)
        2: 3.80,   # February (Anchor Month)
        3: 3.72,   # March (Decision: Mar 18)
        4: 3.65,   # April (Decision: Apr 29)
        5: 3.55,   # May (Anchor Month)
        6: 3.48,   # June (Decision: Jun 17)
        7: 3.40,   # July (Decision: Jul 29)
        8: 3.35,   # August (Anchor Month)
        9: 3.25,   # September (Decision: Sep 16)
        10: 3.20,  # October (Anchor Month)
        11: 3.10,  # November (Decision: Nov 5)
        12: 3.00,  # December (Decision: Dec 16)
    }

    results = run_forward_chain(
        calendar=CALENDAR_2026,
        futures_rates=sample_futures_rates,
        initial_rate=starting_effr,
    )

    # 1. Assert exactly 8 FOMC meetings were processed
    assert len(results) == 8, f"Expected 8 meetings, got {len(results)}"

    print("=" * 82)
    print("FORWARD CHAINING TEST RUN - FOMC 2026")
    print(f"Base Rate (EFFR): {starting_effr:.2f}%")
    print("=" * 82)

    header = f"{'Meeting Date':<14} | {'R_pre':<7} | {'R_post':<7} | {'Var(bps)':<9} | {'H_m':<7} | {'p_low':<7} | {'p_high':<7}"
    print(header)
    print("-" * len(header))

    for m in results:
        date_str = f"Month {m['month']:02d}/{m['decision_day']:02d}"
        var_bps = m["expected_change"] * 100
        row = (
            f"{date_str:<14} | "
            f"{m['r_pre']:.3f}% | "
            f"{m['r_post']:.3f}% | "
            f"{var_bps:+6.1f} bp | "
            f"{m['h_m']:+6.3f} | "
            f"{m['p_low']*100:5.1f}% | "
            f"{m['p_high']*100:5.1f}%"
        )
        print(row)

        # 2. Check conditional probabilities sum to 1.0
        prob_sum = m["p_low"] + m["p_high"]
        assert abs(prob_sum - 1.0) < 1e-4, f"Conditional probabilities do not sum to 1.0 at {date_str}: {prob_sum}"

        # 3. Check cumulative distribution sums to 1.0
        cum_sum = sum(m["cumulative_dist"].values())
        assert abs(cum_sum - 1.0) < 1e-4, f"Cumulative distribution does not sum to 1.0 at {date_str}: {cum_sum}"

    print("\n" + "=" * 82)
    print("FINAL CUMULATIVE PROBABILITY DISTRIBUTION (December 2026):")
    print("=" * 82)
    last_meeting_dist = results[-1]["cumulative_dist"]
    for change, prob in sorted(last_meeting_dist.items()):
        print(f"  Cumulative Move {change:+.2f}% ({int(change*100):+4d} bps): {prob * 100:5.1f}%")

    print("\nTest completed successfully: all assertions passed.")


if __name__ == "__main__":
    test_chain_execution()
