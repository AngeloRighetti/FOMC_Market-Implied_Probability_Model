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
    futures_rates: dict[int, float],
    initial_rate: float,
) -> list[dict[str, Any]]:
    """
    Executes the sequential forward chaining across all calendar months (Section 5.2).
    Propagates rates and applies discrete convolution to track cumulative probabilities.
    """
    results: list[dict[str, Any]] = []
    current_dist: dict[float, float] = {0.0: 1.0}
    r_pre: float = initial_rate

    for idx, month_data in enumerate(calendar):
        month_num = month_data["month"]
        n_m = month_data["days_in_month"]
        m_m = month_data["decision_day"]
        r_avg = futures_rates[month_num]

        # Ispezione del mese successivo (m+1) per la Next-Month Rule
        if idx + 1 < len(calendar):
            next_month_data = calendar[idx + 1]
            next_month_has_meeting = next_month_data["decision_day"] is not None
            r_avg_next = futures_rates[next_month_data["month"]]
        else:
            next_month_has_meeting = False
            r_avg_next = None

        if m_m is not None:
            # 1. Calcolo del tasso post-meeting con eventuale Next-Month Rule
            r_post = resolve_post_meeting_rate(
                next_month_has_meeting=next_month_has_meeting,
                r_avg=r_avg,
                r_pre=r_pre,
                n_m=n_m,
                m_m=m_m,
                r_avg_next=r_avg_next,
            )

            # 2. Scomposizione della mossa attesa nei due scalini discreti
            h_m, lower_step, p_low, upper_step, p_high = extract_meeting_probabilities(
                r_post=r_post,
                r_pre=r_pre,
            )

            # 3. Convoluzione cumulativa dello stato probabilistico
            current_dist = convolve_meeting_step(
                current_dist=current_dist,
                lower_step=lower_step,
                p_low=p_low,
                upper_step=upper_step,
                p_high=p_high,
            )

            # 4. Archiviazione dei risultati per il meeting corrente
            results.append({
                "month": month_num,
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

            # 5. Propagazione del tasso post-meeting (Eq. 20)
            r_pre = r_post
        else:
            # CASO B: Anchor Month (nessun meeting, Eq. 19)
            r_pre = r_avg

    return results


if __name__ == "__main__":
    from calendar_data import CALENDAR_2026

    # 1. Tasso EFFR iniziale prima del primo meeting dell'anno
    starting_effr = 4.33

    # 2. Curva forward simulata dei Fed Funds (R_avg = 100 - Prezzo Future)
    sample_futures_rates = {
        1: 4.28,   # Gennaio (Meeting il 28)
        2: 4.20,   # Febbraio (Anchor Month)
        3: 4.12,   # Marzo (Meeting il 18)
        4: 4.05,   # Aprile (Meeting il 29)
        5: 3.95,   # Maggio (Meeting il 6)
        6: 3.88,   # Giugno (Meeting il 17)
        7: 3.80,   # Luglio (Meeting il 29)
        8: 3.75,   # Agosto (Anchor Month)
        9: 3.65,   # Settembre (Meeting il 16)
        10: 3.58,  # Ottobre (Anchor Month)
        11: 3.48,  # Novembre (Meeting il 5)
        12: 3.40,  # Dicembre (Meeting il 16)
    }

    print("=" * 80)
    print("ESECUZIONE FORWARD CHAINING - FOMC 2026")
    print(f"Tasso di partenza (EFFR): {starting_effr:.2f}%")
    print("=" * 80)

    # 3. Chiamata all'orchestratore
    chain_results = run_forward_chain(
        calendar=CALENDAR_2026,
        futures_rates=sample_futures_rates,
        initial_rate=starting_effr,
    )

    # 4. Stampa formattata dei risultati meeting per meeting
    header = f"{'Data':<12} | {'R_pre':<7} | {'R_post':<7} | {'Var(bps)':<9} | {'H_m':<7} | {'p_low':<7} | {'p_high':<7}"
    print(header)
    print("-" * len(header))

    for m in chain_results:
        date_str = f"Mese {m['month']:02d}/{m['decision_day']:02d}"
        var_bps = m["expected_change"] * 100
        row = (
            f"{date_str:<12} | "
            f"{m['r_pre']:.3f}% | "
            f"{m['r_post']:.3f}% | "
            f"{var_bps:+6.1f} bp | "
            f"{m['h_m']:+6.3f} | "
            f"{m['p_low']*100:5.1f}% | "
            f"{m['p_high']*100:5.1f}%"
        )
        print(row)

    print("\n" + "=" * 80)
    print("DISTRIBUZIONE DI PROBABILITA CUMULATA FINALE (A Fine Anno):")
    print("=" * 80)
    last_meeting_dist = chain_results[-1]["cumulative_dist"]
    for change, prob in sorted(last_meeting_dist.items()):
        print(f"  Variazione cumulata {change:+.2f}% ({int(change*100):+4d} bps): {prob * 100:5.1f}%")