"""Planar (equatorial, eastward) ascent in an inertial frame with Earth rotation, ISA drag, back-pressure thrust, staging and
gravity-turn / pitch-program guidance. Variable-step DOP853 integration. Level 2. Point-mass gravity, no winds, no angle of attack lift."""
import math
from dataclasses import dataclass, replace
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
from backend.core.constants import MU_EARTH as MU, R_EARTH, OMEGA_EARTH as W, G0
from backend.earth.atmosphere import rho_p
from backend.propulsion.rocket import Stage, ideal_delta_v, stage_start_masses
@dataclass
class Vehicle:
    stages: list; payload: float; cd: float = 0.3; ref_area: float = 1.2
@dataclass
class Guidance:
    kick_deg: float = 2.0; t_kick: float = 8.0; kick_dur: float = 4.0; pitch2_deg: float = 30.0; coast_s: float = 2.0; reserve: float = 0.05
def illustrative_vehicle(payload=50.0):
    """Hypothetical small two-stage launcher for demonstration. NOT a real vehicle; numbers are design inputs, not data."""
    return Vehicle([Stage(800, 9000, 220e3, 311, 0.5, "stage1"), Stage(300, 2800, 28e3, 350, 0.2, "stage2")], payload)
def _rhs(stage, g, v, powered, idx, t0, burn):
    kick = math.radians(g.kick_deg); p2 = math.radians(g.pitch2_deg); k = 0.5 * v.cd * v.ref_area
    def f(t, y):
        x, z, vx, vz, m = y; r = math.hypot(x, z); rx, rz = x / r, z / r; ex, ez = rz, -rx
        rho, p, _ = rho_p(r - R_EARTH); ux, uz = vx - W * z, vz + W * x; ur = math.hypot(ux, uz)
        ax = -MU * x / r**3 - k * rho * ur * ux / m; az = -MU * z / r**3 - k * rho * ur * uz / m; md = 0.0
        if powered:
            T = stage.thrust(p)
            if idx == 0:
                if t < g.t_kick: dx, dz = rx, rz
                elif t < g.t_kick + g.kick_dur: dx, dz = math.cos(kick) * rx + math.sin(kick) * ex, math.cos(kick) * rz + math.sin(kick) * ez
                else: dx, dz = (ux / ur, uz / ur) if ur > 1 else (rx, rz)
            else:
                ph = p2 * (1 - (t - t0) / burn); dx, dz = math.cos(ph) * ex + math.sin(ph) * rx, math.cos(ph) * ez + math.sin(ph) * rz
            ax += T / m * dx; az += T / m * dz; md = -stage.mdot
        return [vx, vz, ax, az, md]
    return f
def planar_orbit(x, z, vx, vz):
    r = math.hypot(x, z); eps = (vx*vx + vz*vz) / 2 - MU / r; h = x * vz - z * vx
    if eps >= 0: return {"bound": False, "specific_energy": eps}
    a = -MU / (2 * eps); e = math.sqrt(max(0.0, 1 + 2 * eps * h * h / MU**2))
    return {"bound": True, "a_m": a, "e": e, "perigee_alt_m": a * (1 - e) - R_EARTH, "apogee_alt_m": a * (1 + e) - R_EARTH, "specific_energy": eps}
def simulate_ascent(v, g=None, dt=1.0, rtol=1e-9):
    g = g or Guidance(); m0s = stage_start_masses(v.stages, v.payload); y = np.array([0.0, R_EARTH, W * R_EARTH, 0.0, m0s[0]]); t = 0.0
    T, Y, idx, ev = [], [], [], [{"t": 0.0, "event": "liftoff"}]
    def run(stage, k, powered, dur):
        nonlocal t, y
        te = np.unique(np.append(np.arange(t, t + dur, dt), t + dur))
        s = solve_ivp(_rhs(stage, g, v, powered, k, t, dur), (t, t + dur), y, method="DOP853", rtol=rtol, atol=[1e-3, 1e-3, 1e-5, 1e-5, 1e-4], t_eval=te)
        T.extend(s.t); Y.extend(s.y.T); idx.extend([k if powered else -1] * len(s.t)); t += dur; y = s.y[:, -1].copy()
    for k, s in enumerate(v.stages):
        last = k == len(v.stages) - 1; run(s, k, True, s.prop_mass * ((1 - g.reserve) if last else 1.0) / s.mdot)
        ev.append({"t": t, "event": f"{s.name}_burnout" if not last else "final_cutoff"})
        if not last:
            y[4] -= s.dry_mass; ev.append({"t": t, "event": f"{s.name}_separation"}); run(s, k, False, g.coast_s)
    T = np.array(T); Y = np.array(Y); x, z, vx, vz, m = Y.T; r = np.hypot(x, z); alt = r - R_EARTH
    ux, uz = vx - W * z, vz + W * x; ur = np.hypot(ux, uz); rho = np.array([rho_p(a)[0] for a in alt]); q = 0.5 * rho * ur**2
    i = int(np.argmax(q)); ev.append({"t": float(T[i]), "event": "max_q", "altitude_m": float(alt[i]), "q_pa": float(q[i])}); ev.sort(key=lambda e: e["t"])
    sing = (x * vx + z * vz) / (r * np.hypot(vx, vz)); grav_loss = float(np.trapezoid(MU / r**2 * sing, T))
    drag_loss = float(np.trapezoid(0.5 * rho * ur**2 * v.cd * v.ref_area / m, T)); orb = planar_orbit(*Y[-1][:4])
    s1 = v.stages[0]; twr = s1.thrust(101325.0) / (m0s[0] * G0)
    return {"time_s": T, "altitude_m": alt, "speed_rel_m_s": ur, "mass_kg": m, "dynamic_pressure_pa": q, "events": ev, "orbit_at_cutoff": orb,
            "max_q_pa": float(q[i]), "max_q_altitude_m": float(alt[i]), "ideal_delta_v_m_s": ideal_delta_v(v.stages, v.payload),
            "gravity_loss_m_s": grav_loss, "drag_loss_m_s": drag_loss, "liftoff_twr": twr, "final_mass_kg": float(m[-1]), "reserve_prop_kg": v.stages[-1].prop_mass * g.reserve, "guidance": g}
def optimize_guidance(v, g0=None, maxiter=40):
    g0 = g0 or Guidance()
    def cost(p):
        g = replace(g0, kick_deg=float(np.clip(p[0], .1, 10)), pitch2_deg=float(np.clip(p[1], 0, 80))); o = simulate_ascent(v, g, dt=2.0, rtol=1e-7)["orbit_at_cutoff"]
        return -o["perigee_alt_m"] / 1e3 if o["bound"] else 1e4
    r = minimize(cost, [g0.kick_deg, g0.pitch2_deg], method="Nelder-Mead", options={"maxiter": maxiter, "xatol": 0.02, "fatol": 0.05})
    return replace(g0, kick_deg=float(np.clip(r.x[0], .1, 10)), pitch2_deg=float(np.clip(r.x[1], 0, 80)))
