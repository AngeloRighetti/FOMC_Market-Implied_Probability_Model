"""
Main entry point for extracting market-implied FOMC policy probabilities.
Fetches real-time EFFR from NY Fed, applies actual Fed Funds futures pricing,
and displays meeting probabilities and cumulative distributions.
"""

import os
import sys
from datetime import date
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.append(str(SRC_DIR))

from calendar_data import get_active_calendar
from chain import run_forward_chain
from data_feed import (
    get_spot_effr,
    fetch_market_implied_rates,
)

# ---------------------------------------------------------------------------
# Terminal rendering helpers
# ---------------------------------------------------------------------------
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

if os.name == "nt":
    os.system("")

USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _style(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def bold(text: str) -> str:
    return _style(text, "1")


def dim(text: str) -> str:
    return _style(text, "2")


INDENT = "  "
GAP = "  "

COLUMNS = [
    ("Meeting", 12, "<"),
    ("Pre", 7, ">"),
    ("Post", 7, ">"),
    ("Exp. move", 10, ">"),
    ("Step", 7, ">"),
    ("Prob", 6, ">"),
    ("Step", 7, ">"),
    ("Prob", 6, ">"),
]
TABLE_WIDTH = sum(w for _, w, _ in COLUMNS) + len(GAP) * (len(COLUMNS) - 1)
BAR_BLOCKS = " ▏▎▍▌▋▊▉█"


def rule(char: str = "─") -> str:
    return INDENT + dim(char * TABLE_WIDTH)


def fmt_bp(value_pct: float, decimals: int = 1) -> str:
    bp = value_pct * 100.0
    if round(bp, decimals) == 0:
        return f"{0:.{decimals}f} bp"
    return f"{bp:+.{decimals}f} bp"


def fmt_prob(p: float) -> str:
    return f"{p * 100:.1f}%"


def hbar(fraction: float, width: int = 30) -> str:
    eighths = round(max(0.0, min(1.0, fraction)) * width * 8)
    full, rem = divmod(eighths, 8)
    return "█" * full + (BAR_BLOCKS[rem] if rem else "")


def print_title(base_rate: float, as_of_date: date, source: str) -> None:
    print()
    print(INDENT + bold("FOMC Policy Rate Expectations (Market-Implied Model)"))
    print(INDENT + dim(f"EFFR: {base_rate:.3f}%  ·  As of: {as_of_date}  ·  Source: {source}"))
    print()


def print_meeting_table(chain_results: list[dict]) -> None:
    if not chain_results:
        print(INDENT + dim("No pending FOMC meetings found."))
        return

    pair_width = COLUMNS[4][1] + len(GAP) + COLUMNS[5][1]
    lead = sum(w for _, w, _ in COLUMNS[:4]) + len(GAP) * 4
    group_row = (
        INDENT
        + " " * lead
        + dim(f"{' Lower step ':─^{pair_width}}")
        + GAP
        + dim(f"{' Upper step ':─^{pair_width}}")
    )

    header_cells = [f"{h:{a}{w}}" for h, w, a in COLUMNS]
    print(rule("━"))
    print(group_row)
    print(INDENT + bold(GAP.join(header_cells)))
    print(rule("─"))

    for m in chain_results:
        date_str = f"{m['year']}-{m['month']:02d}-{m['decision_day']:02d}"
        cells = [
            date_str,
            f"{m['r_pre']:.3f}%",
            f"{m['r_post']:.3f}%",
            fmt_bp(m["expected_change"]),
            fmt_bp(m["lower_step"], decimals=0),
            fmt_prob(m["p_low"]),
            fmt_bp(m["upper_step"], decimals=0),
            fmt_prob(m["p_high"]),
        ]
        padded = [f"{c:{a}{w}}" for c, (_, w, a) in zip(cells, COLUMNS)]
        print(INDENT + GAP.join(padded))

    print(rule("━"))
    print(INDENT + dim("Exp. move: probability-weighted policy adjustment at each FOMC meeting."))


def print_terminal_distribution(chain_results: list[dict], base_rate: float) -> None:
    if not chain_results:
        return

    dist = sorted(chain_results[-1]["cumulative_dist"].items())
    modal = max(prob for _, prob in dist) if dist else 0.0
    last = chain_results[-1]
    label = f"{last['year']}-{last['month']:02d}-{last['decision_day']:02d}"

    print()
    print(INDENT + bold("12-Month Horizon Cumulative Target Rate Distribution"))
    print(INDENT + dim(f"Terminal state after {label} meeting (Base EFFR: {base_rate:.3f}%)"))
    print()

    cols = [("Target", 7, ">"), ("Change", 9, ">"), ("Prob", 6, ">")]
    width = sum(w for _, w, _ in cols) + len(GAP) * len(cols) + 30
    print(INDENT + dim("─" * width))
    print(INDENT + bold(GAP.join(f"{h:{a}{w}}" for h, w, a in cols)))
    print(INDENT + dim("─" * width))

    for cum_change, prob in dist:
        target = base_rate + cum_change
        row = (
            f"{f'{target:.2f}%':>7}"
            + GAP
            + f"{fmt_bp(cum_change):>9}"
            + GAP
            + f"{fmt_prob(prob):>6}"
            + GAP
            + hbar(prob)
        )
        if prob == modal:
            row = bold(row)
        elif prob < 0.01:
            row = dim(row)
        print(INDENT + row)

    print(INDENT + dim("─" * width))


def run_pipeline() -> None:
    """Executes the pipeline with actual market figures."""
    # 1. Fetch spot EFFR via FRED or NY Fed
    base_rate, as_of_date, source_label = get_spot_effr()

    # 2. Get market-implied futures curve
    futures_rates = fetch_market_implied_rates()

    # 3. Active calendar
    active_calendar = get_active_calendar(as_of=as_of_date)

    # 4. Forward chaining
    chain_results = run_forward_chain(
        calendar=active_calendar,
        futures_rates=futures_rates,
        initial_rate=base_rate,
    )

    # 5. Render
    print_title(base_rate, as_of_date, source_label)
    print_meeting_table(chain_results)
    print_terminal_distribution(chain_results, base_rate)
    print()


if __name__ == "__main__":
    run_pipeline()
