"""Mission orchestration: launch -> orbit-raising feasibility (reserve propellant) -> on-orbit power/thermal/link/imaging. Every stage consumes
the previous stage's physical state (mass, altitude, period), so payload mass changes propagate through to delta-v, orbit and power eclipse timing."""
import math
from dataclasses import dataclass
from backend.core.constants import G0, R_EARTH
from backend.orbital_mechanics.orbits import hohmann
from backend.spacecraft import subsystems as ss
from backend.simulation.launch_simulator import simulate_ascent, optimize_guidance, Guidance, Vehicle
@dataclass
class Spacecraft:   # defaults are illustrative design inputs for a small imaging satellite, not catalog data
    array_area_m2: float = 0.5; cell_efficiency: float = 0.28; degradation: float = 0.9; pointing_cos: float = 0.8; load_w: float = 30.0; battery_wh: float = 60.0
    absorptivity: float = 0.6; emissivity: float = 0.8; sun_area_m2: float = 0.3; rad_area_m2: float = 1.0
    freq_hz: float = 8.2e9; tx_power_w: float = 5.0; tx_gain_dbi: float = 8.0; gs_g_over_t_db_k: float = 25.0; data_rate_bps: float = 50e6; required_ebn0_db: float = 4.5
    pixel_pitch_m: float = 7e-6; focal_m: float = 0.5; pixels_across: int = 6000; bits_per_pixel: int = 12; imaging_s_per_orbit: float = 120.0
def simulate_mission(v: Vehicle, sc: Spacecraft, target_alt_m: float, beta_deg: float = 20.0, optimize: bool = True, guidance: Guidance | None = None):
    g = guidance or (optimize_guidance(v) if optimize else Guidance()); L = simulate_ascent(v, g); orb = L["orbit_at_cutoff"]
    out = {"fidelity_level": "L2-engineering", "events": [dict(e) for e in L["events"]], "launch": {k: L[k] for k in ["max_q_pa", "max_q_altitude_m", "ideal_delta_v_m_s", "gravity_loss_m_s", "drag_loss_m_s", "liftoff_twr", "final_mass_kg"]}, "orbit_at_cutoff": orb}
    if not orb["bound"] or orb["perigee_alt_m"] < 120e3:
        out.update(status="failed_to_reach_stable_orbit", failure="insufficient_energy_or_perigee_below_120km"); return out
    last = v.stages[-1]; prop = L["reserve_prop_kg"]; dv_have = last.isp_vac * G0 * math.log(L["final_mass_kg"] / (L["final_mass_kg"] - prop)) if prop > 0 else 0.0
    h = hohmann(R_EARTH + orb["perigee_alt_m"], R_EARTH + target_alt_m)["dv_total_m_s"] if abs(target_alt_m - orb["perigee_alt_m"]) > 1e3 else 0.0
    out["orbit_raising"] = {"required_dv_m_s": h, "available_dv_m_s": dv_have, "feasible": dv_have >= h}
    if dv_have < h: out.update(status="orbit_not_reached", failure="insufficient_reserve_delta_v"); return out
    beta = math.radians(beta_deg); gen = ss.array_power(sc.array_area_m2, sc.cell_efficiency, sc.degradation, sc.pointing_cos)
    pw = ss.orbit_power_profile(target_alt_m, beta, gen, sc.load_w, sc.battery_wh)
    th = {"sunlit_K": ss.equilibrium_temperature_k(sc.absorptivity, sc.emissivity, sc.sun_area_m2, sc.rad_area_m2, sc.load_w), "eclipse_K": ss.equilibrium_temperature_k(sc.absorptivity, sc.emissivity, 1e-9, sc.rad_area_m2, sc.load_w, 0.0)}
    lk = ss.link_budget(target_alt_m, math.radians(10), sc.freq_hz, sc.tx_power_w, sc.tx_gain_dbi, sc.gs_g_over_t_db_k, sc.data_rate_bps, sc.required_ebn0_db)
    im = ss.imaging(target_alt_m, sc.pixel_pitch_m, sc.focal_m, sc.pixels_across, sc.bits_per_pixel, sc.imaging_s_per_orbit)
    flags = [n for n, bad in [("power_blackout", pw["blackout_s"] > 0), ("negative_power_margin", pw["orbit_avg_margin_w"] < 0), ("link_margin_below_3dB", lk["margin_db"] < 3)] if bad]
    out.update(status="operational" if not flags else "degraded", flags=flags, power={"generation_w_sunlit": gen, **pw}, thermal=th, link=lk, imaging=im); return out
