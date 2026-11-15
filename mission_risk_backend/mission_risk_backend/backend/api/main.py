"""FastAPI service. Versioned under /v1. Inputs validated by Pydantic; physics errors become HTTP 422, never stack traces."""
import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.earth.atmosphere import atmosphere
from backend.orbital_mechanics.orbits import hohmann, period, eclipse_fraction
from backend.core.constants import R_EARTH
from backend.propulsion.rocket import Stage
from backend.simulation.launch_simulator import Vehicle, Guidance, simulate_ascent, illustrative_vehicle
from backend.simulation.mission_simulator import Spacecraft, simulate_mission
from backend.risk.monte_carlo import delta_v_margin
from backend.spacecraft import subsystems as ss
app = FastAPI(title="Mission Risk Physics API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:8000", "http://localhost:8000", "null"], allow_methods=["POST", "GET"], allow_headers=["*"])
class StageIn(BaseModel):
    dry_mass: float = Field(gt=0); prop_mass: float = Field(gt=0); thrust_vac: float = Field(gt=0); isp_vac: float = Field(gt=100, lt=500); exit_area: float = Field(ge=0); name: str = "stage"
class VehicleIn(BaseModel):
    stages: list[StageIn] = Field(min_length=1, max_length=4); payload: float = Field(gt=0); cd: float = Field(0.3, gt=0, lt=2); ref_area: float = Field(1.2, gt=0)
def _veh(v): return Vehicle([Stage(**s.model_dump()) for s in v.stages], v.payload, v.cd, v.ref_area)
@app.get("/v1/health")
def health(): return {"status": "ok", "version": "0.1.0"}
class AtmIn(BaseModel): altitude_m: float = Field(ge=-1000, le=2e6)
@app.post("/v1/atmosphere")
def atm(b: AtmIn): return atmosphere(b.altitude_m)
class HohIn(BaseModel): r1_alt_m: float = Field(gt=0); r2_alt_m: float = Field(gt=0)
@app.post("/v1/orbit/hohmann")
def hoh(b: HohIn): return {**hohmann(R_EARTH + b.r1_alt_m, R_EARTH + b.r2_alt_m), "fidelity_level": "L1-analytic"}
class OrbIn(BaseModel): altitude_m: float = Field(gt=100e3, lt=40e6); beta_deg: float = Field(0, ge=-90, le=90)
@app.post("/v1/orbit/summary")
def orb(b: OrbIn):
    return {"period_s": period(R_EARTH + b.altitude_m), "eclipse_fraction": eclipse_fraction(b.altitude_m, math.radians(b.beta_deg)), "fidelity_level": "L1-analytic"}
class LaunchIn(BaseModel): vehicle: VehicleIn | None = None; kick_deg: float = Field(2.0, gt=0, le=10); pitch2_deg: float = Field(30.0, ge=0, le=80)
@app.post("/v1/launch/simulate")
def launch(b: LaunchIn):
    v = _veh(b.vehicle) if b.vehicle else illustrative_vehicle(); r = simulate_ascent(v, Guidance(kick_deg=b.kick_deg, pitch2_deg=b.pitch2_deg), dt=2.0)
    step = max(1, -(-len(r["time_s"]) // 120))
    return {"fidelity_level": "L2-engineering", "events": r["events"], "orbit_at_cutoff": r["orbit_at_cutoff"], "liftoff_twr": r["liftoff_twr"], "max_q_pa": r["max_q_pa"],
            "gravity_loss_m_s": r["gravity_loss_m_s"], "drag_loss_m_s": r["drag_loss_m_s"], "ideal_delta_v_m_s": r["ideal_delta_v_m_s"],
            "telemetry": {k: [float(x) for x in r[k][::step]] for k in ["time_s", "altitude_m", "speed_rel_m_s", "mass_kg", "dynamic_pressure_pa"]}}
class LinkIn(BaseModel):
    altitude_m: float = Field(gt=100e3, lt=40e6); elevation_deg: float = Field(10, ge=0, le=90); freq_hz: float = Field(gt=1e8, lt=1e11); tx_power_w: float = Field(gt=0)
    tx_gain_dbi: float; gs_g_over_t_db_k: float; data_rate_bps: float = Field(gt=0); required_ebn0_db: float = 4.5
@app.post("/v1/spacecraft/link")
def link(b: LinkIn): return {**ss.link_budget(b.altitude_m, math.radians(b.elevation_deg), b.freq_hz, b.tx_power_w, b.tx_gain_dbi, b.gs_g_over_t_db_k, b.data_rate_bps, b.required_ebn0_db), "fidelity_level": "L1-analytic"}
class RiskIn(BaseModel): vehicle: VehicleIn; required_delta_v_m_s: float = Field(gt=0); n: int = Field(1000, ge=10, le=20000); seed: int = 0; sigma_isp: float = Field(0.01, ge=0, le=0.1); sigma_dry: float = Field(0.02, ge=0, le=0.2)
@app.post("/v1/risk/delta-v")
def risk(b: RiskIn):
    v = _veh(b.vehicle); return {**delta_v_margin(v.stages, v.payload, b.required_delta_v_m_s, b.n, b.seed, b.sigma_isp, b.sigma_dry), "note": "physical-uncertainty margin; not a historical failure rate"}
class MissionIn(BaseModel): vehicle: VehicleIn | None = None; target_alt_m: float = Field(500e3, gt=200e3, lt=2e6); beta_deg: float = 20.0
@app.post("/v1/mission/simulate")
def mission(b: MissionIn):
    try: return simulate_mission(_veh(b.vehicle) if b.vehicle else illustrative_vehicle(), Spacecraft(), b.target_alt_m, b.beta_deg, optimize=True)
    except (ValueError, ZeroDivisionError) as e: raise HTTPException(422, f"physics error: {e}")
