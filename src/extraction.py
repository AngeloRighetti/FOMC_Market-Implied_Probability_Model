def extract_post_meeting_rate(r_avg: float, r_pre: float, n_m: int, m_m: int) -> float:
    """
    Computes the expected post-meeting rate for a single month (Eq. 7, methodology.pdf) 
    """
    numerator = (n_m * r_avg) - (m_m * r_pre)
    denominator = (n_m - m_m)
    r_post = numerator / denominator
    return r_post

def resolve_post_meeting_rate(
    next_month_has_meeting : bool, 
    r_avg : float, 
    r_pre : float, 
    n_m : int, 
    m_m : int, 
    r_avg_next: float | None = None, 
    threshold_l: int = 7,
    ) -> float:
    """
    Selects and computes the post-meeting rate using either the own-month
    estimator (Eq. 7) or the next-month rule (Eq. 11, methodology.pdf).
    """
    days_remaining = (n_m - m_m)

    if days_remaining >= threshold_l:
        r_post = extract_post_meeting_rate(r_avg, r_pre, n_m, m_m)
    elif days_remaining < threshold_l and not next_month_has_meeting:
        if r_avg_next is None:
            raise ValueError("r_avg_next must be provided when applying the next-month rule.")
        r_post = r_avg_next
    else:  # days_remaining < threshold_l and next_month_has_meeting
        r_post = extract_post_meeting_rate(r_avg, r_pre, n_m, m_m)
    return r_post

def extract_meeting_probabilities(r_post : float, r_pre : float, step : float = 0.25):
    """
    Decompone la variazione attesa nella distribuzione a due punti (Eq. 14-17, methodology.pdf).
    """
    h_m = (r_post - r_pre) / step 
    if h_m >= 0:
        s_m = +1
    else:
        s_m = -1
    abs_h = abs(h_m)
    k_m = int(abs_h)
    alpha_m = abs_h - k_m 

    lower_step = s_m * k_m * step
    upper_step = s_m * (k_m + 1) * step
    
    p_low = 1.0 - alpha_m
    p_high = alpha_m 

    return h_m, lower_step, p_low, upper_step, p_high

r_pre = 3.530
r_post = 3.417
diff = r_post - r_pre
print(f"{diff:.3f}")
h_m, lower_step, p_low, upper_step, p_high = extract_meeting_probabilities(r_post, r_pre)
print(f"h_m: {h_m:.4f}")
print(f"Lower step: {lower_step:.2f} (Probabilità: {p_low * 100:.1f}%)")
print(f"Upper step: {upper_step:.2f} (Probabilità: {p_high * 100:.1f}%)")