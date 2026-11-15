"""Rocket performance: Tsiolkovsky, staging, mass flow, back-pressure-corrected thrust. Level 1-2."""
import math
from dataclasses import dataclass
from backend.core.constants import G0
@dataclass(frozen=True)
class Stage:
    dry_mass: float; prop_mass: float; thrust_vac: float; isp_vac: float; exit_area: float; name: str = "stage"
    @property
    def mdot(self): return self.thrust_vac / (self.isp_vac * G0)            # F = mdot * Isp * g0
    @property
    def burn_time(self): return self.prop_mass / self.mdot
    def thrust(self, p_ambient): return max(0.0, self.thrust_vac - p_ambient * self.exit_area)   # F = F_vac - p_a * A_e
def tsiolkovsky(isp, m0, mf):
    if not (m0 > mf > 0): raise ValueError("require m0 > mf > 0")
    return isp * G0 * math.log(m0 / mf)
def stage_start_masses(stages, payload):
    out = []; above = payload
    for s in reversed(stages): above += s.dry_mass + s.prop_mass; out.append(above)
    return out[::-1]
def ideal_delta_v(stages, payload):
    return sum(tsiolkovsky(s.isp_vac, m0, m0 - s.prop_mass) for s, m0 in zip(stages, stage_start_masses(stages, payload)))
def thrust_to_weight(stage, m0, p_ambient=101325.0): return stage.thrust(p_ambient) / (m0 * G0)
