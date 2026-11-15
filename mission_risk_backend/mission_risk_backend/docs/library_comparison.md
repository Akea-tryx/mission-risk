# Library comparison (PyPI queried 14 Nov 2026; Python 3.12.3, Linux x86_64, 1 CPU, no GPU)
Class: E essential, H highly recommended, S specialized, R research-grade, U unsuitable. "Installed" = imported successfully here. "Used" = called by backend code.
| Library | Version / last release | Python req | License (PyPI) | Class | Decision |
|---|---|---|---|---|---|
| numpy | 2.5.4 / 2026-10 | >=3.12 | BSD | E | Installed, **used** everywhere |
| scipy | 1.18.1 / 2026-08 | >=3.12 | BSD | E | Installed, **used**: DOP853 ODEs, Nelder-Mead guidance optimizer |
| fastapi, pydantic, uvicorn | 0.162.7, 2.14.3, 0.54.0 | >=3.10 | MIT/BSD | E | Installed, **used** for the API |
| pytest, httpx | 9.2.0, 0.28.1 | | MIT/BSD | E (tests) | Installed, **used** (TestClient) |
| sympy | 1.14.0 / 2025-04 | >=3.9 | BSD | H | Installed, not yet used (symbolic cross-checks) |
| pint | 0.26.2 / 2026-10 | >=3.12 | BSD | H | Installed, not yet used (units at API boundary). Backend uses SI internally with no dimensional checks |
| sgp4 | 2.27 / 2026-07 | | MIT | H | Installed, **not yet integrated** (TLE tracking) |
| skyfield | 1.55 / 2026-08 | | MIT | H | Installed, not yet used (passes, ephemerides) |
| astropy | 8.0.2 / 2026-10 | >=3.11 | BSD | H | Installed, not yet used (time scales, frames) |
| numba | 0.68.1 / 2026-10 | >=3.10 | BSD | H | Installed, not needed yet (sim runs in ~20 ms) |
| mpmath, uncertainties | 1.4.1, 3.2.3 | | BSD | O | Not installed; scipy/numpy sufficient |
| pyatmos | 1.2.7 / 2024-11 | >=3.10 | MIT | H (next) | **Not installed.** Needed for thermospheric density (LEO drag/lifetime); ISA module cannot do that |
| pyproj, geographiclib | 3.8.0, 2.1 | | MIT | S | Not installed; no geodesy yet |
| metpy, xarray, netcdf4, cartopy | 1.7.1, 2026.9.0, 1.7.5.1, 0.26.0 | | BSD/MIT | S | Not installed; no weather/wind data yet |
| coolprop | 8.0.0 / 2026-06 | >=3.9 | MIT | S | Not installed; propellant/tank thermodynamics |
| cantera | 3.2.0 / 2025-11 | <3.15 | BSD | S | Not installed; combustion chemistry |
| rocketpy | 1.13.0 / 2026-07 | >=3.10 | (blank in PyPI metadata, **verify**) | S | Not installed; 6-DOF reference for solid/hybrid rockets |
| rocketcea | 1.2.3 / 2026-01 | | GPL (per PyPI) | S | Not installed; **license risk**, needs compiled CEA |
| spiceypy | 8.4.0 / 2026-11 | >=3.10 | MIT | S | Not installed; needs SPICE kernel downloads |
| bsk (Basilisk) | 2.12.2 / 2026-11 | <3.15 | ISC | R | Not installed; high-fidelity spacecraft sim, heavy |
| orekit_jpype | 13.1.9.0 / 2026-10 | | (see PyPI) | R | Not installed; needs Java |
| rebound | 5.2.2 / 2026-10 | >=3.9 | **GPL-3.0** | R | Not installed; N-body, license concern |
| sunpy, plasmapy, galpy | 8.0.1, 2026.2.0, 1.12.1 | >=3.10-3.12 | BSD | R | Not installed; solar/plasma/galactic, outside game scope |
| jax, torch | 0.12.0.1, 2.15.0 | >=3.11-3.12 | Apache | R | Not installed; no differentiable-physics need yet |
| mujoco, pybullet, pydy | 4.0.1, 3.2.7, 0.9.4 | | Apache/zlib/BSD | R | Not installed; rigid-body engines beyond current need |
| sfepy, meshio, pyvista | 2026.3, 5.3.5, 0.49.2 | | BSD/MIT | R | Not installed; FEM and visualization, no structural module yet |
| **poliastro** | 0.17.0 / **2022-07** | **>=3.8,<3.11** | | **U** | Incompatible with Python 3.12 and unmaintained |
| hapsira | 0.18.0 / 2023-12 | >=3.8 | | U (stale) | Fork of poliastro; no release since 2023-12, not installed |
| wrf-python, ambiance | 1.3.4.1 / 2022-05; 1.3.1 / 2022-09 | | Apache | U (stale) | Not installed |
| tudatpy, fenics-dolfinx | **not on PyPI** | | | U here | Conda/system installs only; not attempted |
Not investigated this session: GMAT interfaces, OpenFOAM Python interfaces, SymPy Mechanics (inside sympy).
