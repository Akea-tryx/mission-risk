"""US Standard Atmosphere 1976 (ISA) to 86 km geometric. Above that a crude isothermal extension is used:
NOT valid for LEO drag/lifetime (real thermospheric density is far higher). Level: 1-2."""
import math
from backend.core.constants import G0, R_AIR, GAMMA_AIR, R_EARTH_ISA
_H = [0.0, 11000.0, 20000.0, 32000.0, 47000.0, 51000.0, 71000.0, 84852.0]   # geopotential base heights, m
_L = [-0.0065, 0.0, 0.0010, 0.0028, 0.0, -0.0028, -0.0020]                   # lapse rates, K/m
_T = [288.15]; _P = [101325.0]
for _i, _l in enumerate(_L):
    _dh = _H[_i + 1] - _H[_i]; _t0 = _T[_i]
    _t1 = _t0 + _l * _dh
    _P.append(_P[_i] * (math.exp(-G0 * _dh / (R_AIR * _t0)) if _l == 0 else (_t1 / _t0) ** (-G0 / (_l * R_AIR)))); _T.append(_t1)
def rho_p(h):
    """Fast path: (density kg/m^3, pressure Pa, temperature K) at geometric altitude h (m)."""
    h = max(float(h), -5000.0); hg = R_EARTH_ISA * h / (R_EARTH_ISA + h)
    if hg >= _H[-1]:
        T = _T[-1]; p = _P[-1] * math.exp(-G0 * (hg - _H[-1]) / (R_AIR * T)); return p / (R_AIR * T), p, T
    i = 0
    while i < 6 and hg >= _H[i + 1]: i += 1
    l = _L[i]; dh = hg - _H[i]; T = _T[i] + l * dh
    p = _P[i] * (math.exp(-G0 * dh / (R_AIR * _T[i])) if l == 0 else (T / _T[i]) ** (-G0 / (l * R_AIR)))
    return p / (R_AIR * T), p, T
def atmosphere(h):
    rho, p, T = rho_p(h)
    return {"altitude_m": h, "temperature_K": T, "pressure_Pa": p, "density_kg_m3": rho,
            "speed_of_sound_m_s": math.sqrt(GAMMA_AIR * R_AIR * T), "model": "ISA-1976" if h < 86000 else "crude_extension_above_86km"}
