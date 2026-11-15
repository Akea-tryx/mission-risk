# Mission Risk Physics Backend (v0.1)

Physics simulation service and REST API for space mission planning, orbital mechanics, launch ascent simulation, and spacecraft subsystem budgets.

## Quick Start

### 1. Requirements & Setup
- Python 3.10+ (tested on Python 3.12 / 3.9)
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Run Tests
```bash
python -m pytest -q
```

### 3. Run the API Server
```bash
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation and OpenAPI schemas are available at `http://127.0.0.1:8000/docs`.

---

## Architecture & Modules

| Module | Physics Domain | Fidelity Level | Implementation Details |
|---|---|---|---|
| `earth/atmosphere` | Earth Atmosphere | L1-2 | ISA-1976 standard atmosphere to 86 km geometric altitude (temperature lapse rates, pressure, density, speed of sound) and isothermal upper extension. |
| `earth/gravity_field` | Gravitational Field | L2 | Point-mass central gravity plus Earth oblateness $J_2$ perturbation in Earth-Centered Inertial (ECI) coordinates. |
| `propulsion/rocket` | Rocket Dynamics | L1-2 | Ideal Tsiolkovsky delta-v, multi-stage sequential burnout, mass flow rate, and back-pressure nozzle expansion compensation. |
| `orbital_mechanics/orbits` | Orbital Mechanics | L1-3 | Cartesian state vector to Keplerian elements conversion, numerical orbit propagation (DOP853 Runge-Kutta), Hohmann transfers, $J_2$ nodal precession, sun-synchronous inclination, and cylindrical eclipse fraction. |
| `spacecraft/subsystems` | Spacecraft Subsystems | L1-2 | Solar array output with incidence angle and degradation, orbital battery discharge profile through eclipses, lumped-capacitance thermal equilibrium, RF link budgets (FSPL, EIRP, $C/N_0$, $E_b/N_0$), optical payload ground sampling distance (GSD), and torque-free rigid-body attitude dynamics. |
| `simulation/launch_simulator` | Ascent Simulation | L2 | Planar equatorial eastward ascent with rotating Earth inertial frame, atmospheric drag, dynamic pressure (max-Q), stage separation, gravity-turn pitch guidance, and Nelder-Mead guidance optimization. |
| `simulation/mission_simulator` | Mission Pipeline | L2 | End-to-end mission evaluation propagating ascent cutoff conditions to orbit-raising feasibility, power balance, thermal states, and data downlink margins. |
| `risk/monte_carlo` | Risk & Uncertainty | L1 | Physical uncertainty Monte Carlo evaluation for delta-v margins across dry mass, payload mass, and engine specific impulse variations. |

---

## REST API Specification (`/v1`)

All endpoints validate JSON payloads via Pydantic schemas. Invalid parameters return HTTP 422 with structured validation errors.

- `GET /v1/health`: Returns server status and version.
- `POST /v1/atmosphere`: Calculates temperature, pressure, density, and sound speed for a given altitude.
- `POST /v1/orbit/hohmann`: Computes delta-v and transfer time for two-impulse Hohmann transfers.
- `POST /v1/orbit/summary`: Computes orbital period and eclipse fraction for a circular orbit.
- `POST /v1/launch/simulate`: Simulates rocket launch trajectory, staging events, max-Q, and cutoff orbit.
- `POST /v1/spacecraft/link`: Computes RF link margins given transmitter power, antenna gains, and ground station parameters.
- `POST /v1/risk/delta-v`: Runs Monte Carlo uncertainty simulation on vehicle delta-v margin.
- `POST /v1/mission/simulate`: Executes full end-to-end mission simulation (launch + orbit insertion + subsystems).

---

## Frontend Integration & Connectivity

The backend connects directly to the Godot frontend client via HTTP:
- Endpoint Base: `http://127.0.0.1:8000/v1`
- CORS: Configured with `CORSMiddleware` to allow requests from local game instances (`http://127.0.0.1:8000`, `http://localhost:8000`, and `null` origin for native/desktop clients).
- Client Handler: `autoload/ApiClient.gd` in the Godot project manages asynchronous request dispatching (`/v1/health`, `/v1/launch/simulate`, `/v1/mission/simulate`) and updates game state with live physics telemetry.
