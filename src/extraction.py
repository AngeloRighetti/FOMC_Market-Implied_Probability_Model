def extract_post_meeting_rate(r_avg, r_pre, n_m, m_m) -> float:
    """
    Computes the expected post-meeting rate for a single month (Eq. 7, methodology.pdf) 
    """
    numerator = (n_m * r_avg) - (m_m * r_pre)
    denominator = (n_m - m_m)
    r_post = numerator / denominator
    return r_post

r_pre_december = 3.5300
p_december = 96.5500
r_avg_december = 100 - p_december
m_december = 9
n_december = 31

r_post_dec = extract_post_meeting_rate(r_avg_december, r_pre_december, n_december, m_december)
print (f"""
The expected post-meeting rate for december is: 3.4173%.
The effective post-meeting rate for december is: {r_post_dec:.4f}%
""")