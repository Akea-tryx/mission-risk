import math, numpy as np, pytest
from fastapi.testclient import TestClient
from backend.core.constants import G0, MU_EARTH, R_EARTH, R_EARTH_ISA
from backend.earth.atmosphere import atmosphere
from backend.propulsion.rocket import Stage, tsiolkovsky, ideal_delta_v
from backend.orbital_mechanics import orbits as ob
from backend.spacecraft import subsystems as ss
from backend.simulation.launch_simulator import (
    Vehicle, simulate_ascent, illustrative_vehicle, optimize_guidance
)
from backend.simulation.mission_simulator import Spacecraft, simulate_mission
from backend.risk.monte_carlo import delta_v_margin
from backend.api.main import app
client = TestClient(app)
@pytest.fixture(scope="module")
def vehicle(): return illustrative_vehicle()
@pytest.fixture(scope="module")
def guidance(vehicle): return optimize_guidance(vehicle, maxiter=60)
# ---- atmosphere vs published ISA-1976 table values
@pytest.mark.parametrize("h,p,T", [(0, 101325.0, 288.15), (11000, 22632.06, 216.65), (20000, 5474.889, 216.65), (32000, 868.0187, 228.65)])
def test_isa_reference(h, p, T):
    h = R_EARTH_ISA * h / (R_EARTH_ISA - h)      # published ISA tables list GEOPOTENTIAL altitude; the model takes geometric altitude
    a = atmosphere(h); assert a["pressure_Pa"] == pytest.approx(p, rel=5e-4) and a["temperature_K"] == pytest.approx(T, abs=0.02)
def test_isa_sea_level_density_and_sound_speed():
    a = atmosphere(0); assert a["density_kg_m3"] == pytest.approx(1.225, rel=1e-3) and a["speed_of_sound_m_s"] == pytest.approx(340.29, rel=1e-3)
def test_isa_hydrostatic_balance():
    h = 5000.0; d = 1.0; dpdh = (atmosphere(h + d)["pressure_Pa"] - atmosphere(h - d)["pressure_Pa"]) / (2 * d)
    g_local = G0 * (R_EARTH_ISA / (R_EARTH_ISA + h)) ** 2     # dp/dh_geometric = -rho * g0 * dH/dh
    assert dpdh == pytest.approx(-atmosphere(h)["density_kg_m3"] * g_local, rel=2e-3)
# ---- propulsion
def test_tsiolkovsky_analytic(): assert tsiolkovsky(300, math.e, 1.0) == pytest.approx(300 * G0, rel=1e-12)
def test_mass_flow_and_burn_time():
    s = Stage(100, 900, 50e3, 300, 0.1); assert s.mdot * s.isp_vac * G0 == pytest.approx(s.thrust_vac) and s.burn_time == pytest.approx(900 / s.mdot)
def test_back_pressure_thrust(): s = Stage(1, 1, 1000, 300, 0.2); assert s.thrust(0) == 1000 and s.thrust(101325) == pytest.approx(1000 - 101325 * 0.2) or s.thrust(101325) == 0
def test_staged_delta_v_hand_calc():
    st = [Stage(100, 900, 1e4, 300, .1), Stage(20, 180, 2e3, 350, .1)]; p = 10.0
    m1 = 100 + 900 + 20 + 180 + p; m2 = 20 + 180 + p; ref = 300 * G0 * math.log(m1 / (m1 - 900)) + 350 * G0 * math.log(m2 / (m2 - 180))
    assert ideal_delta_v(st, p) == pytest.approx(ref, rel=1e-12)
# ---- orbital mechanics
def test_circular_orbit_period_and_conservation():
    a = R_EARTH + 500e3; r0, v0 = ob.elements_to_state(a, 0.0, math.radians(51.6), 0.3, 0, 0); T = ob.period(a)
    t, r, v = ob.propagate(r0, v0, 10 * T, 400, use_j2=False); E = 0.5 * (v**2).sum(1) - MU_EARTH / np.linalg.norm(r, axis=1); H = np.linalg.norm(np.cross(r, v), axis=1)
    assert np.ptp(E) / abs(E[0]) < 1e-9 and np.ptp(H) / H[0] < 1e-9
    t2, r2, v2 = ob.propagate(r0, v0, T, 3, use_j2=False); assert np.linalg.norm(r2[-1] - r0) / a < 1e-7      # returns to start after one analytic period
def test_elliptical_orbit_roundtrip_and_period():
    r, v = ob.elements_to_state(9e6, 0.3, 1.0, 1.1, 0.7, 2.0); el = ob.state_to_elements(r, v)
    assert (el["a_m"], el["e"], el["i_rad"], el["raan_rad"], el["argp_rad"], el["nu_rad"]) == pytest.approx((9e6, 0.3, 1.0, 1.1, 0.7, 2.0), rel=1e-9)
def test_escape_velocity_zero_energy():
    r = R_EARTH + 300e3; v = math.sqrt(2 * MU_EARTH / r); assert (0.5 * v * v - MU_EARTH / r) == pytest.approx(0, abs=1e-3)
def test_hohmann_leo_geo():
    r1, r2 = R_EARTH + 300e3, 42164e3; v1, v2 = math.sqrt(MU_EARTH / r1), math.sqrt(MU_EARTH / r2)
    ref = v1 * (math.sqrt(2 * r2 / (r1 + r2)) - 1) + v2 * (1 - math.sqrt(2 * r1 / (r1 + r2)))       # textbook closed form, independent of the code's vis-viva route
    assert ob.hohmann(r1, r2)["dv_total_m_s"] == pytest.approx(ref, rel=1e-9) and ref == pytest.approx(3.9e3, rel=0.02)
def test_sun_synchronous_inclination_700km():
    assert math.degrees(ob.sun_synchronous_inclination(R_EARTH + 700e3)) == pytest.approx(98.19, abs=0.05)
def test_j2_raan_drift_numeric_vs_analytic():
    a = R_EARTH + 700e3; i = math.radians(98.19); r0, v0 = ob.elements_to_state(a, 0.001, i, 1.0, 0.5, 0.0)
    t, r, v = ob.propagate(r0, v0, 86400.0, 50, use_j2=True); d = ob.state_to_elements(r[-1], v[-1])["raan_rad"] - 1.0
    assert d == pytest.approx(ob.j2_raan_rate(a, 0.001, i) * 86400.0, rel=0.03)
def test_eclipse_fraction_numeric_vs_analytic():
    alt = 500e3; a = R_EARTH + alt; i, O = math.radians(30), math.radians(60); r0, v0 = ob.elements_to_state(a, 0, i, O, 0, 0)
    beta = math.asin(np.cross(r0, v0)[0] / np.linalg.norm(np.cross(r0, v0)))      # sun along +x
    t, r, v = ob.propagate(r0, v0, ob.period(a), 4000, use_j2=False); shadow = (r[:, 0] < 0) & (np.hypot(r[:, 1], r[:, 2]) < R_EARTH)
    assert shadow.mean() == pytest.approx(ob.eclipse_fraction(alt, beta), abs=0.004)
def test_eclipse_none_at_high_beta(): assert ob.eclipse_fraction(500e3, math.radians(80)) == 0.0
# ---- spacecraft
def test_fspl_reference_formula():
    d, f = 1000e3, 2.2e9; assert ss.fspl_db(d, f) == pytest.approx(92.45 + 20 * math.log10(d / 1e3) + 20 * math.log10(f / 1e9), abs=0.05)
def test_link_margin_monotonic_with_power():
    a = ss.link_budget(500e3, .17, 8.2e9, 2, 8, 25, 5e7, 4.5); b = ss.link_budget(500e3, .17, 8.2e9, 4, 8, 25, 5e7, 4.5); assert b["margin_db"] - a["margin_db"] == pytest.approx(10 * math.log10(2), abs=1e-9)
def test_blackbody_sphere_temperature_1au(): assert ss.equilibrium_temperature_k(1, 1, math.pi, 4 * math.pi) == pytest.approx(278.3, abs=1.0)
def test_battery_discharge_matches_analytic_eclipse_energy():
    alt = 500e3; p = ss.orbit_power_profile(alt, 0.0, 100.0, 50.0, 1000.0, n_orbits=1, dt=5.0); Te = p["eclipse_fraction"] * p["period_s"]
    assert 1000 - p["min_soc_wh"] == pytest.approx(50 * Te / 3600 / 0.95, rel=0.01) and p["blackout_s"] == 0
def test_battery_blackout_when_undersized():
    p = ss.orbit_power_profile(500e3, 0.0, 100.0, 90.0, 5.0, n_orbits=2); assert p["blackout_s"] > 0
def test_imaging_gsd_and_data_rate():
    im = ss.imaging(500e3, 7e-6, 0.5, 6000, 12, 120); assert im["gsd_m"] == pytest.approx(7.0) and im["swath_m"] == pytest.approx(42000.0)
def test_torque_free_attitude_conserves_H_and_energy():
    s = ss.torque_free_attitude([1, 2, 3], [0.1, 2.0, 0.1], 100.0)
    assert np.ptp(s["H_norm"]) / s["H_norm"][0] < 1e-8 and np.ptp(s["kinetic_energy"]) / s["kinetic_energy"][0] < 1e-8 and np.allclose(np.linalg.norm(s["quat"], axis=1), 1, atol=1e-8)
# ---- launch simulation (coupled physics)
def test_vehicle_reaches_stable_orbit(vehicle, guidance):
    o = simulate_ascent(vehicle, guidance)["orbit_at_cutoff"]; assert o["bound"] and o["perigee_alt_m"] > 120e3
def test_mass_bookkeeping_and_events(vehicle, guidance):
    r = simulate_ascent(vehicle, guidance); s1, s2 = vehicle.stages; m0 = 800 + 9000 + 300 + 2800 + 50
    assert r["mass_kg"][0] == pytest.approx(m0) and r["final_mass_kg"] == pytest.approx(m0 - s1.prop_mass - s1.dry_mass - s2.prop_mass * (1 - guidance.reserve), rel=1e-6)
    assert {"liftoff", "max_q", "stage1_separation", "final_cutoff"} <= {e["event"] for e in r["events"]} and r["liftoff_twr"] > 1.0
def test_max_q_physically_plausible(vehicle, guidance):
    r = simulate_ascent(vehicle, guidance); assert 5e3 < r["max_q_altitude_m"] < 20e3 and 1e4 < r["max_q_pa"] < 8e4
def test_more_drag_costs_performance(vehicle, guidance):
    a = simulate_ascent(vehicle, guidance); b = simulate_ascent(Vehicle(vehicle.stages, vehicle.payload, cd=0.9, ref_area=vehicle.ref_area), guidance)
    assert b["drag_loss_m_s"] > a["drag_loss_m_s"] and b["orbit_at_cutoff"]["perigee_alt_m"] < a["orbit_at_cutoff"]["perigee_alt_m"]
def test_payload_mass_propagates_to_delta_v_and_orbit(vehicle, guidance):
    heavy = Vehicle(vehicle.stages, 120.0, vehicle.cd, vehicle.ref_area)
    assert ideal_delta_v(heavy.stages, 120.0) < ideal_delta_v(vehicle.stages, 50.0)
    assert simulate_ascent(heavy, guidance)["orbit_at_cutoff"]["perigee_alt_m"] < simulate_ascent(vehicle, guidance)["orbit_at_cutoff"]["perigee_alt_m"]
def test_mission_operational_and_coupled(vehicle, guidance):
    m = simulate_mission(vehicle, Spacecraft(), 500e3, 20, guidance=guidance); assert m["status"] == "operational" and m["orbit_raising"]["feasible"]
    assert m["power"]["period_s"] == pytest.approx(ob.period(R_EARTH + 500e3)) and m["imaging"]["gsd_m"] == pytest.approx(7.0)
    low = simulate_mission(vehicle, Spacecraft(load_w=500.0), 500e3, 20, guidance=guidance); assert low["status"] == "degraded" and "negative_power_margin" in low["flags"]
def test_overweight_payload_fails_to_orbit(vehicle):
    m = simulate_mission(illustrative_vehicle(400.0), Spacecraft(), 500e3, optimize=False); assert m["status"].startswith(("failed", "orbit_not"))
# ---- risk
def test_monte_carlo_deterministic_and_monotonic(vehicle):
    a = delta_v_margin(vehicle.stages, 50, 10900, n=500, seed=1); b = delta_v_margin(vehicle.stages, 50, 10900, n=500, seed=1); c = delta_v_margin(vehicle.stages, 50, 11100, n=500, seed=1)
    assert a == b and c["prob_negative_margin"] > a["prob_negative_margin"] and a["mean_margin_m_s"] == pytest.approx(ideal_delta_v(vehicle.stages, 50) - 10900, abs=30)
# ---- API
def test_api_health_atmosphere_validation():
    assert client.get("/v1/health").json()["status"] == "ok"
    assert client.post("/v1/atmosphere", json={"altitude_m": 0}).json()["density_kg_m3"] == pytest.approx(1.225, rel=1e-3)
    assert client.post("/v1/atmosphere", json={"altitude_m": 1e9}).status_code == 422
def test_api_hohmann_and_orbit_summary():
    r = client.post("/v1/orbit/hohmann", json={"r1_alt_m": 300e3, "r2_alt_m": 35786e3}).json(); assert r["dv_total_m_s"] == pytest.approx(3.9e3, rel=0.02)
    assert 0 < client.post("/v1/orbit/summary", json={"altitude_m": 500e3}).json()["eclipse_fraction"] < 0.5
def test_api_launch_link_risk_mission():
    L = client.post("/v1/launch/simulate", json={"kick_deg": 0.5, "pitch2_deg": 6.6}).json(); assert L["orbit_at_cutoff"]["bound"] and len(L["telemetry"]["time_s"]) <= 130
    k = client.post("/v1/spacecraft/link", json={"altitude_m": 500e3, "freq_hz": 8.2e9, "tx_power_w": 5, "tx_gain_dbi": 8, "gs_g_over_t_db_k": 25, "data_rate_bps": 5e7}).json(); assert k["margin_db"] > 0
    stg = {"dry_mass": 800, "prop_mass": 9000, "thrust_vac": 220e3, "isp_vac": 311, "exit_area": 0.5}
    assert client.post("/v1/risk/delta-v", json={"vehicle": {"stages": [stg], "payload": 50}, "required_delta_v_m_s": 3000, "n": 200}).status_code == 200
    assert client.post("/v1/risk/delta-v", json={"vehicle": {"stages": [], "payload": 50}, "required_delta_v_m_s": 3000}).status_code == 422
    assert client.post("/v1/mission/simulate", json={}).json()["status"] in ("operational", "degraded")
