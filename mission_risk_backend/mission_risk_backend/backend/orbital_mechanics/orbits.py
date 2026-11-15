"""Orbital mechanics: elements<->state, two-body/J2 propagation (DOP853), Hohmann, sun-sync, eclipse. Level 2-3."""
import math, numpy as np
from scipy.integrate import solve_ivp
from backend.core.constants import MU_EARTH as MU, R_EARTH, J2
from backend.earth.gravity_field import accel_j2
def period(a): return 2 * math.pi * math.sqrt(a**3 / MU)
def circular_speed(r): return math.sqrt(MU / r)
def elements_to_state(a, e, i, raan, argp, nu):
    p = a * (1 - e**2); r = p / (1 + e * math.cos(nu))
    rp = np.array([r * math.cos(nu), r * math.sin(nu), 0.0]); vp = math.sqrt(MU / p) * np.array([-math.sin(nu), e + math.cos(nu), 0.0])
    cO, sO, ci, si, cw, sw = math.cos(raan), math.sin(raan), math.cos(i), math.sin(i), math.cos(argp), math.sin(argp)
    R = np.array([[cO*cw - sO*sw*ci, -cO*sw - sO*cw*ci, sO*si], [sO*cw + cO*sw*ci, -sO*sw + cO*cw*ci, -cO*si], [sw*si, cw*si, ci]])
    return R @ rp, R @ vp
def state_to_elements(r, v):
    r = np.asarray(r, float); v = np.asarray(v, float); rn = np.linalg.norm(r); h = np.cross(r, v); hn = np.linalg.norm(h)
    ev = np.cross(v, h) / MU - r / rn; e = np.linalg.norm(ev); a = 1 / (2 / rn - v @ v / MU)
    i = math.acos(h[2] / hn); n = np.cross([0, 0, 1], h); nn = np.linalg.norm(n)
    raan = math.atan2(n[1], n[0]) % (2*math.pi) if nn > 1e-12 else 0.0
    argp = (math.acos(np.clip(n @ ev / (nn * e), -1, 1)) * (1 if ev[2] >= 0 else -1)) % (2*math.pi) if nn > 1e-12 and e > 1e-12 else 0.0
    nu = (math.acos(np.clip(ev @ r / (e * rn), -1, 1)) * (1 if r @ v >= 0 else -1)) % (2*math.pi) if e > 1e-12 else 0.0
    return {"a_m": a, "e": e, "i_rad": i, "raan_rad": raan, "argp_rad": argp, "nu_rad": nu}
def propagate(r0, v0, duration, n_points=200, use_j2=True, rtol=1e-10):
    f = lambda t, y: np.r_[y[3:], accel_j2(y[:3], use_j2)]
    sol = solve_ivp(f, (0, duration), np.r_[r0, v0], method="DOP853", rtol=rtol, atol=1e-6, t_eval=np.linspace(0, duration, n_points))
    return sol.t, sol.y[:3].T, sol.y[3:].T
def hohmann(r1, r2):
    at = (r1 + r2) / 2; dv1 = abs(math.sqrt(MU * (2/r1 - 1/at)) - math.sqrt(MU/r1)); dv2 = abs(math.sqrt(MU/r2) - math.sqrt(MU * (2/r2 - 1/at)))
    return {"dv1_m_s": dv1, "dv2_m_s": dv2, "dv_total_m_s": dv1 + dv2, "transfer_time_s": math.pi * math.sqrt(at**3 / MU)}
def j2_raan_rate(a, e, i):
    p = a * (1 - e**2); n = math.sqrt(MU / a**3); return -1.5 * J2 * (R_EARTH / p)**2 * n * math.cos(i)
def sun_synchronous_inclination(a, e=0.0):
    need = 2 * math.pi / (365.2421897 * 86400); p = a * (1 - e**2); n = math.sqrt(MU / a**3)
    return math.acos(need / (-1.5 * J2 * (R_EARTH / p)**2 * n))
def eclipse_fraction(alt_m, beta_rad=0.0):
    """Cylindrical-shadow eclipse fraction of a circular orbit; beta = angle between Sun vector and orbit plane."""
    r = R_EARTH + alt_m
    if abs(beta_rad) >= math.asin(R_EARTH / r): return 0.0
    return math.acos(math.sqrt(alt_m**2 + 2 * R_EARTH * alt_m) / (r * math.cos(beta_rad))) / math.pi
