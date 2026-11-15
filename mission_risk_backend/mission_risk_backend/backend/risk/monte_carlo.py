"""Physical-uncertainty Monte Carlo on delta-v margin. Sigmas are USER-SUPPLIED assumptions. This is NOT a historical launch-failure statistic
and must never be mixed with GCAT/NTRS-style success rates or component reliability data."""
import numpy as np
from backend.propulsion.rocket import Stage, ideal_delta_v
def delta_v_margin(stages, payload, required_delta_v, n=2000, seed=0, sigma_isp=0.01, sigma_dry=0.02, sigma_payload=0.02):
    rng = np.random.default_rng(seed); out = np.empty(n)
    for k in range(n):
        s = [Stage(st.dry_mass * rng.normal(1, sigma_dry), st.prop_mass, st.thrust_vac, st.isp_vac * rng.normal(1, sigma_isp), st.exit_area, st.name) for st in stages]
        out[k] = ideal_delta_v(s, payload * rng.normal(1, sigma_payload)) - required_delta_v
    return {"n": n, "seed": seed, "mean_margin_m_s": float(out.mean()), "std_margin_m_s": float(out.std()), "p05_m_s": float(np.percentile(out, 5)),
            "prob_negative_margin": float((out < 0).mean()), "assumptions": {"sigma_isp": sigma_isp, "sigma_dry": sigma_dry, "sigma_payload": sigma_payload}}
