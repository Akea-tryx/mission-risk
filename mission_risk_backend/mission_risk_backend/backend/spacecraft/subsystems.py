"""Spacecraft subsystem physics: power+battery, lumped thermal, RF link budget, imaging geometry, torque-free attitude. Level 1-2."""
import math, numpy as np
from scipy.integrate import solve_ivp
from backend.core.constants import SOLAR_CONSTANT as S, SIGMA_SB, C_LIGHT, K_B, MU_EARTH, R_EARTH
from backend.orbital_mechanics.orbits import period, eclipse_fraction
def array_power(area_m2, efficiency, degradation=1.0, cos_incidence=1.0): return S * area_m2 * efficiency * degradation * max(cos_incidence, 0.0)
def orbit_power_profile(alt_m, beta_rad, gen_w_sun, load_w, battery_wh, n_orbits=5, dt=10.0, eta_c=0.95, eta_d=0.95):
    """Step a circular orbit through sunlight/eclipse; battery starts full. Returns min state of charge and blackout flag."""
    T = period(R_EARTH + alt_m); fe = eclipse_fraction(alt_m, beta_rad); soc = battery_wh; low = battery_wh; black = 0.0
    for k in range(int(n_orbits * T / dt)):
        ph = (k * dt % T) / T; eclipse = abs(ph - 0.5) < fe / 2; net = (0.0 if eclipse else gen_w_sun) - load_w
        if net >= 0: soc = min(battery_wh, soc + net * eta_c * dt / 3600)
        else:
            need = -net * dt / 3600 / eta_d
            if soc >= need: soc -= need
            else: soc = 0.0; black += dt
        low = min(low, soc)
    return {"period_s": T, "eclipse_fraction": fe, "min_soc_wh": low, "depth_of_discharge": 1 - low / battery_wh, "blackout_s": black,
            "orbit_avg_margin_w": gen_w_sun * (1 - fe) - load_w}
def equilibrium_temperature_k(absorptivity, emissivity, area_sun, area_rad, internal_w=0.0, flux=S):
    return ((absorptivity * flux * area_sun + internal_w) / (emissivity * SIGMA_SB * area_rad)) ** 0.25   # ignores Earth albedo/IR
def fspl_db(distance_m, freq_hz): return 20 * math.log10(4 * math.pi * distance_m * freq_hz / C_LIGHT)
def slant_range(alt_m, elevation_rad):
    Re = R_EARTH; return -Re * math.sin(elevation_rad) + math.sqrt((Re * math.sin(elevation_rad))**2 + alt_m**2 + 2 * Re * alt_m)
def link_budget(alt_m, elevation_rad, freq_hz, tx_power_w, tx_gain_dbi, gs_g_over_t_db_k, data_rate_bps, required_ebn0_db, other_losses_db=2.0):
    d = slant_range(alt_m, elevation_rad); eirp = 10 * math.log10(tx_power_w) + tx_gain_dbi; fs = fspl_db(d, freq_hz)
    cn0 = eirp - fs - other_losses_db + gs_g_over_t_db_k - 10 * math.log10(K_B); ebn0 = cn0 - 10 * math.log10(data_rate_bps)
    return {"slant_range_m": d, "fspl_db": fs, "eirp_dbw": eirp, "cn0_dbhz": cn0, "ebn0_db": ebn0, "margin_db": ebn0 - required_ebn0_db}
def doppler_hz(freq_hz, radial_speed_m_s): return freq_hz * radial_speed_m_s / C_LIGHT
def imaging(alt_m, pixel_pitch_m, focal_m, pixels_across, bits_per_pixel, duty_s_per_orbit):
    gsd = alt_m * pixel_pitch_m / focal_m; swath = gsd * pixels_across; r = R_EARTH + alt_m
    ground_speed = math.sqrt(MU_EARTH / r) * R_EARTH / r; rate = (swath / gsd) * (ground_speed / gsd) * bits_per_pixel
    orbits_day = 86400 / period(r)
    return {"gsd_m": gsd, "swath_m": swath, "ground_speed_m_s": ground_speed, "data_rate_bps": rate, "gb_per_day": rate * duty_s_per_orbit * orbits_day / 8e9}
def torque_free_attitude(inertia_diag, w0, duration, n_points=200, q0=(1, 0, 0, 0)):
    I = np.array(inertia_diag, float)
    def f(t, y):
        w = y[:3]; q = y[3:]; dw = -np.cross(w, I * w) / I
        wq = np.array([0, *w]); a = q; b = wq
        dq = 0.5 * np.array([a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3], a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2], a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1], a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]])
        return np.r_[dw, dq]
    s = solve_ivp(f, (0, duration), np.r_[w0, q0], method="DOP853", rtol=1e-11, atol=1e-13, t_eval=np.linspace(0, duration, n_points))
    w = s.y[:3].T; H = np.linalg.norm(w * I, axis=1); Ek = 0.5 * np.sum(I * w**2, axis=1)
    return {"t": s.t, "omega": w, "quat": s.y[3:].T, "H_norm": H, "kinetic_energy": Ek}
