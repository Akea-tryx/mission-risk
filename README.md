# RIFT: Space Command & Mission Risk Physics Simulation

A unified space mission planning, risk evaluation, and orbital flight simulation platform. The project combines a 3D first-person mission control client built in Godot Engine with a high-fidelity Python FastAPI physics backend.

---

## System Architecture

```
                                  +---------------------------------------+
                                  |         Godot 4 Game Client           |
                                  |     (RIFT: Space Command / UI)        |
                                  +-------------------+-------------------+
                                                      |
                                             HTTP (REST / JSON)
                                          autoload/ApiClient.gd
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |         FastAPI Physics Backend       |
                                  |          (Port 8000 / /v1)            |
                                  +-------------------+-------------------+
                                                      |
        +-------------------------+-------------------+-------------------------+
        |                         |                   |                         |
        v                         v                   v                         v
+---------------+         +---------------+   +---------------+         +---------------+
|  Atmosphere   |         |    Launch     |   |    Orbital    |         |  Spacecraft   |
|  & Gravity    |         |  Trajectory   |   |   Mechanics   |         |  Subsystems   |
| (ISA-1976/J2) |         | (DOP853/MaxQ) |   | (Hohmann/J2)  |         | (Power/Link)  |
+---------------+         +---------------+   +---------------+         +---------------+
```

The system comprises two core components:
1. **Frontend (`mission-risk-(4.3)`)**: A Godot Engine 4 (4.3+) project featuring 3D first-person mission control rooms, interactive terminals, component catalog selection, budget allocation, and mission outcome visualization.
2. **Backend (`mission_risk_backend`)**: A high-performance Python FastAPI service delivering numerical orbital mechanics, atmospheric models, multi-stage rocket ascent trajectory integration, and satellite subsystem calculations.
3. **Connectivity Layer (`ApiClient.gd`)**: An asynchronous HTTP network client that connects the Godot game loop to the FastAPI REST API over `http://127.0.0.1:8000/v1`.

---

## Directory Structure

```
.
├── README.md                          # Project documentation
├── mission_risk_backend/              # Python FastAPI Physics Backend
│   └── mission_risk_backend/
│       ├── backend/
│       │   ├── api/                   # REST API routes (main.py)
│       │   ├── core/                  # Physical constants (constants.py)
│       │   ├── earth/                 # Atmosphere (ISA-1976) & gravity (J2)
│       │   ├── orbital_mechanics/     # Keplerian elements, DOP853 propagation
│       │   ├── propulsion/            # Tsiolkovsky, rocket staging, nozzle losses
│       │   ├── risk/                  # Monte Carlo delta-v margin evaluation
│       │   ├── simulation/            # Launch ascent & mission simulators
│       │   ├── spacecraft/            # Power, battery, thermal, RF link budget
│       │   └── tests/                 # Comprehensive unit & physics tests
│       ├── requirements.txt           # Production Python dependencies
│       └── requirements.lock.txt      # Exact locked package versions
└── mission-risk-(4.3)/                # Godot Engine Frontend Client
    └── mission-risk-(4.3)/
        ├── project.godot              # Godot 4 project definition & autoloads
        ├── autoload/
        │   ├── ApiClient.gd           # HTTP connectivity manager for backend API
        │   ├── GameState.gd           # Central gameplay state & telemetry store
        │   └── MissionState.gd        # Mission catalog selection & constraints
        ├── data/
        │   ├── catalog.json           # Spacecraft bus, launchers, instruments
        │   └── narrative.json         # Dialogue and mission dossiers
        └── scenes/
            ├── MainGame.tscn          # 3D interactive first-person environment
            ├── MainDashboard.tscn     # Detailed telemetry and engineering UI
            └── Boardroom.tscn         # Mission briefing scene
```

---

## Setup & Execution Guide

### 1. Running the Physics Backend

1. Navigate to the backend directory:
   ```bash
   cd mission_risk_backend/mission_risk_backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows PowerShell:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the automated test suite (36 tests verifying physical conservation laws and API schemas):
   ```bash
   python -m pytest -q
   ```

5. Launch the FastAPI server:
   ```bash
   uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. Confirm the backend is running by opening `http://127.0.0.1:8000/docs` in your browser.

---

### 2. Running the Godot Frontend

1. Download and install **Godot Engine 4.3 (or 4.x stable)** from [godotengine.org](https://godotengine.org).
2. Open the Godot Project Manager, click **Import**, and select:
   `mission-risk-(4.3)/mission-risk-(4.3)/project.godot`
3. Click **Import & Edit**.
4. Press **F5** (or click the Play button in the top right) to launch the simulation.

---

## How Connectivity Works

Network communication between Godot and FastAPI is established via Godot's built-in `HTTPRequest` node inside `autoload/ApiClient.gd`.

1. **Automatic Handshake**:
   When Godot boots, `ApiClient._ready()` sends a `GET /v1/health` request to `http://127.0.0.1:8000/v1/health`. If successful, `GameState.backend_connected` is set to `true`.

2. **Flight Telemetry Dispatch**:
   During the launch countdown in `MainGame.gd`, the client calls:
   ```gdscript
   ApiClient.simulate_launch(kick_deg, pitch2_deg)
   ```
   This sends a `POST /v1/launch/simulate` request with vehicle trajectory parameters.

3. **Physics Integration & Graceful Fallback**:
   - **When Connected**: The backend returns exact trajectory telemetry, stage burnout times, dynamic pressure (max-Q), and orbit cutoff parameters (perigee, apogee). The outcome is validated against real orbital bounds ($r_{\text{perigee}} \ge 120\text{ km}$).
   - **When Offline**: The game client automatically detects the offline state and falls back to local gameplay risk calculations without interrupting the user experience.

---

## API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/health` | Health check endpoint returning server status. |
| `POST` | `/v1/atmosphere` | ISA-1976 barometric calculation up to 86 km. |
| `POST` | `/v1/orbit/hohmann` | Delta-v and transfer duration for circular orbit transfers. |
| `POST` | `/v1/orbit/summary` | Orbital period and solar eclipse fraction. |
| `POST` | `/v1/launch/simulate` | Planar ascent integration with dynamic pressure, gravity losses, and stage cutoff. |
| `POST` | `/v1/spacecraft/link` | RF communication link budget ($C/N_0$, $E_b/N_0$, margins). |
| `POST` | `/v1/risk/delta-v` | Monte Carlo delta-v uncertainty distribution under physical variations. |
| `POST` | `/v1/mission/simulate` | Full end-to-end mission profile from liftoff to on-orbit subsystem health. |
