"""
FOMC Market-Implied Probability Model
Single-file execution script with manual data inputs.
Reference: methodology.pdf
"""

import os
import sys

# =========================================================================
# 1. MANUAL INPUT SECTION (Update these values based on current market data)
# =========================================================================

# The current observation date and base rate (Effective Federal Funds Rate)
AS_OF_DATE = "2026-10-31"
SPOT_EFFR = 3.880

# 30-Day Fed Funds Futures (CME ZQ) Settlement Prices
# Format: (Year, Month): Price
FUTURES_PRICES = {
    (2026, 12): 95.937,  # Implies 4.063%
    (2027, 1):  95.847,  # Implies 4.153%
    (2027, 2):  95.847,  # Anchor month (No meeting)
    (2027, 3):  95.745,  # Implies 4.255%
    (2027, 4):  95.654,  # Implies 4.346%
    (2027, 5):  95.654,  # Anchor month (No meeting)
    (2027, 6):  95.593,  # Implies 4.407%
    (2027, 7):  95.568,  # Implies 4.432%
    (2027, 8):  95.568,  # Anchor month (No meeting)
    (2027, 9):  95.561,  # Implies 4.439%
    (2027, 10): 95.565,  # Implies 4.435%
}

# The active calendar of upcoming FOMC meetings. 
# Remove past meetings manually to keep the horizon clean.
FOMC_CALENDAR = [
    {"year": 2026, "month": 12, "days_in_month": 31, "decision_day": 9},
    {"year": 2027, "month": 1,  "days_in_month": 31, "decision_day": 27},
    {"year": 2027, "month": 2,  "days_in_month": 28, "decision_day": None}, # No meeting
    {"year": 2027, "month": 3,  "days_in_month": 31, "decision_day": 17},
    {"year": 2027, "month": 4,  "days_in_month": 30, "decision_day": 28},
    {"year": 2027, "month": 5,  "days_in_month": 31, "decision_day": None},
    {"year": 2027, "month": 6,  "days_in_month": 30, "decision_day": 9},
    {"year": 2027, "month": 7,  "days_in_month": 31, "decision_day": 28},
    {"year": 2027, "month": 8,  "days_in_month": 31, "decision_day": None},
    {"year": 2027, "month": 9,  "days_in_month": 30, "decision_day": 15},
    {"year": 2027, "month": 10, "days_in_month": 31, "decision_day": 27},
]


# =========================================================================
# 2. MATHEMATICAL CORE (Referencing methodology.pdf)
# =========================================================================

def extract_post_meeting_rate(r_avg: float, r_pre: float, n_m: int, m_m: int) -> float:
    """
    Eq. 7: Implied post-meeting rate for a standard meeting month.
    Extracts the expected target rate assuming the policy change occurs on day m_m.
    """
    return (n_m * r_avg - m_m * r_pre) / (n_m - m_m)

def resolve_post_meeting_rate(
    next_month_has_meeting: bool, r_avg: float, r_pre: float, 
    n_m: int, m_m: int, r_avg_next: float | None
) -> float:
    """
    Eq. 11 (Next-Month Rule): Handles standard and late-month meetings.
    Prevents calculation spikes when m_m is close to the end of the month (n_m).
    """
    days_remaining = n_m - m_m
    
    # Case 1: Standard meeting (>= 7 days left in the month) -> Use Eq. 7
    if days_remaining >= 7:
        return extract_post_meeting_rate(r_avg, r_pre, n_m, m_m)
    
    # Case 2: Late-month meeting AND next month is an anchor (no meeting) -> Use Eq. 11
    if days_remaining < 7 and not next_month_has_meeting:
        if r_avg_next is not None:
            return r_avg_next # The next month's average fully reflects the post-meeting rate
        # Boundary fallback if curve ends
        return extract_post_meeting_rate(r_avg, r_pre, n_m, m_m)
        
    # Case 3: Late-month meeting but next month also has a meeting -> Use Eq. 7
    return extract_post_meeting_rate(r_avg, r_pre, n_m, m_m)

def extract_meeting_probabilities(r_post: float, r_pre: float, step: float = 0.25) -> tuple:
    """
    Eq. 14-17: Decomposes the expected rate change into two discrete 25 bps policy steps.
    Returns: continuous change (h_m), lower step, prob lower, upper step, prob upper.
    """
    h_m = (r_post - r_pre) / step
    # Determine the number of standard steps (k_m)
    k_m = int(h_m) if h_m >= 0 else int(h_m) - (1 if h_m % 1 != 0 else 0)
    
    lower_step = k_m * step
    upper_step = (k_m + 1) * step
    
    p_high = h_m - k_m
    p_low = 1.0 - p_high
    
    return h_m, lower_step, p_low, upper_step, p_high

def convolve_meeting_step(
    current_dist: dict[float, float], lower_step: float, 
    p_low: float, upper_step: float, p_high: float
) -> dict[float, float]:
    """
    Eq. 23: Discrete convolution to update the cumulative probability distribution.
    Propagates uncertainty meeting-by-meeting through the tree of possible rate paths.
    """
    new_dist: dict[float, float] = {}
    
    for cum_change, prob in current_dist.items():
        if p_low > 0:
            c1 = round(cum_change + lower_step, 4)
            new_dist[c1] = new_dist.get(c1, 0.0) + (prob * p_low)
        if p_high > 0:
            c2 = round(cum_change + upper_step, 4)
            new_dist[c2] = new_dist.get(c2, 0.0) + (prob * p_high)
            
    return new_dist

def run_forward_chain() -> list[dict]:
    """
    Section 5.2 (Forward Chaining): Orchestrates the propagation of rates 
    and probabilities chronologically through the FOMC calendar.
    """
    results = []
    current_dist = {0.0: 1.0}
    r_pre = SPOT_EFFR
    
    # Convert futures prices to average implied rates (R = 100 - P)
    implied_rates = {k: round(100.0 - v, 4) for k, v in FUTURES_PRICES.items()}

    for idx, month_data in enumerate(FOMC_CALENDAR):
        y, m = month_data["year"], month_data["month"]
        n_m, m_m = month_data["days_in_month"], month_data["decision_day"]
        
        key = (y, m)
        if key not in implied_rates:
            continue
            
        r_avg = implied_rates[key]
        
        # Lookahead logic for the Next-Month Rule (Eq. 11)
        if idx + 1 < len(FOMC_CALENDAR):
            next_m = FOMC_CALENDAR[idx + 1]
            next_has_meeting = next_m["decision_day"] is not None
            r_avg_next = implied_rates.get((next_m["year"], next_m["month"]))
        else:
            next_has_meeting = False
            r_avg_next = None

        if m_m is not None:
            # Step 1: Calculate post-meeting rate
            r_post = resolve_post_meeting_rate(next_has_meeting, r_avg, r_pre, n_m, m_m, r_avg_next)
            # Step 2: Extract branch probabilities
            h_m, l_step, p_low, u_step, p_high = extract_meeting_probabilities(r_post, r_pre)
            # Step 3: Update cumulative distribution
            current_dist = convolve_meeting_step(current_dist, l_step, p_low, u_step, p_high)
            
            # Save results
            results.append({
                "year": y, "month": m, "day": m_m,
                "r_pre": r_pre, "r_post": r_post, "exp_change": r_post - r_pre,
                "l_step": l_step, "p_low": p_low, "u_step": u_step, "p_high": p_high,
                "cum_dist": current_dist.copy()
            })
            r_pre = r_post
        else:
            # Anchor month: Pre-rate carries over naturally
            r_pre = r_avg
            
    return results


# =========================================================================
# 3. TERMINAL RENDERING DASHBOARD
# =========================================================================

# Ensure block characters render correctly on all operating systems
try:
    sys.stdout.reconfigure(encoding="utf-8")
except:
    pass
if os.name == "nt":
    os.system("")

def print_dashboard(results: list[dict]):
    """Renders the formatted results to the terminal output."""
    def fmt_bp(v: float, dec: int = 1) -> str:
        bp = v * 100.0
        return f"{0:.{dec}f} bp" if round(bp, dec) == 0 else f"{bp:+.{dec}f} bp"

    def hbar(frac: float, width: int = 30) -> str:
        eighths = round(max(0.0, min(1.0, frac)) * width * 8)
        full, rem = divmod(eighths, 8)
        return "█" * full + (" ▏▎▍▌▋▊▉█"[rem] if rem else "")

    print("\n  \033[1mFOMC Policy Rate Expectations (Market-Implied Model)\033[0m")
    print(f"  \033[2mEFFR: {SPOT_EFFR:.3f}%  ·  As of: {AS_OF_DATE}  ·  Source: Manual Input\033[0m\n")
    
    if not results:
        print("  \033[2mNo pending FOMC meetings found.\033[0m")
        return

    # Table Header
    print("  \033[2m────────────────────────────────────────────────────────────────────────────────────\033[0m")
    print("                                            \033[2m── Lower step ──  ── Upper step ──\033[0m")
    print("  \033[1mMeeting      Pre      Post     Exp. move  Step     Prob     Step     Prob\033[0m")
    print("  \033[2m────────────────────────────────────────────────────────────────────────────────────\033[0m")

    for r in results:
        d_str = f"{r['year']}-{r['month']:02d}-{r['day']:02d}"
        print(f"  {d_str:<12} {r['r_pre']:.3f}%  {r['r_post']:.3f}%  "
              f"{fmt_bp(r['exp_change']):>9}  "
              f"{fmt_bp(r['l_step'], 0):>7}  {r['p_low']*100:>5.1f}%  "
              f"{fmt_bp(r['u_step'], 0):>7}  {r['p_high']*100:>5.1f}%")

    print("  \033[2m────────────────────────────────────────────────────────────────────────────────────\033[0m")
    
    # Distribution Header
    last = results[-1]
    dist = sorted(last["cum_dist"].items())
    modal = max(p for _, p in dist) if dist else 0.0
    
    print(f"\n  \033[1m12-Month Horizon Cumulative Target Rate Distribution\033[0m")
    print(f"  \033[2mTerminal state after {last['year']}-{last['month']:02d}-{last['day']:02d} meeting\033[0m\n")
    
    print("  \033[2m──────────────────────────────────────────────────────────\033[0m")
    print("  \033[1m Target    Change    Prob\033[0m")
    print("  \033[2m──────────────────────────────────────────────────────────\033[0m")
    
    for cum_change, prob in dist:
        target = SPOT_EFFR + cum_change
        row = f"  {target:>6.2f}%  {fmt_bp(cum_change):>8}  {prob*100:>5.1f}%  {hbar(prob)}"
        if prob == modal:
            print(f"\033[1m{row}\033[0m")
        elif prob < 0.01:
            print(f"\033[2m{row}\033[0m")
        else:
            print(row)
            
    print("  \033[2m──────────────────────────────────────────────────────────\033[0m\n")

if __name__ == "__main__":
    chain_results = run_forward_chain()
    print_dashboard(chain_results)