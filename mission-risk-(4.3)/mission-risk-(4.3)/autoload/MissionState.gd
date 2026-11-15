class_name MissionState
extends Node

## MissionRisk Physics & State Engine
## Loads catalog and narrative data, calculates mission constraints, emits live metrics

signal state_updated(metrics: Dictionary)

# Data references
var _catalog: Dictionary = {}
var _narrative: Dictionary = {}

# Mission configuration (selected by user)
var selected_mission: Dictionary = {}
var selected_orbit: Dictionary = {}
var selected_launcher: Dictionary = {}
var selected_bus: Dictionary = {}
var selected_power: Dictionary = {}
var selected_battery: Dictionary = {}
var selected_comms: Dictionary = {}
var selected_adcs: Dictionary = {}
var selected_propulsion: Dictionary = {}
var instruments: Array = []  # Array of selected instruments

# System parameters
var mission_role_sign_offs: Dictionary = {
	"director": false,
	"scientist": false,
	"engineer": false,
	"comms": false
}

# Computed metrics (updated by recalculate_mission)
var total_cost: float = 0.0
var total_mass: float = 0.0
var raw_power_generation_watts: float = 0.0
var peak_power_load_watts: float = 0.0
var power_margin_pct: float = 0.0
var eclipse_battery_drain_amp_hrs: float = 0.0
var usable_battery_capacity_amp_hrs: float = 0.0
var data_capture_ratio: float = 0.0
var effective_science_yield: float = 0.0
var lifetime_years: float = 0.0

# Alerts (updated by recalculate_mission)
var blockers: Array = []  # Red alerts that prevent launch
var warnings: Array = []  # Yellow alerts that lower score

# Sandbox mode flag (unlimited budget)
var _sandbox_mode: bool = false
var _anomaly_active: bool = false
var _anomaly_penalty_pct: float = 0.0

var actual_cost: float = 0.0


func _ready() -> void:
	_load_data()
	_recalculate_mission()


func _load_data() -> void:
	# Load catalog
	var catalog_file = FileAccess.open("res://data/catalog.json", FileAccess.READ)
	if catalog_file:
		var parsed = JSON.parse_string(catalog_file.get_as_text())
		if parsed is Dictionary:
			_catalog = parsed
		catalog_file.close()

	# Load narrative
	var narrative_file = FileAccess.open("res://data/narrative.json", FileAccess.READ)
	if narrative_file:
		var parsed = JSON.parse_string(narrative_file.get_as_text())
		if parsed is Dictionary:
			_narrative = parsed
		narrative_file.close()


func _recalculate_mission() -> void:
	## Main physics engine: calculates all mission constraints and alerts.
	if selected_mission.is_empty() or selected_bus.is_empty():
		return

	# -- 1. TOTAL COST --
	# Base mission cost + launcher + bus + all instruments + selected components
	var _total_cost = (
		selected_mission.budget_usd
		+ selected_launcher.cost_usd
		+ selected_bus.cost_usd
		+ selected_power.cost_usd
		+ selected_battery.cost_usd
		+ selected_comms.cost_usd
		+ selected_adcs.cost_usd
		+ selected_propulsion.cost_usd
	)

	for inst in instruments:
		if inst is Dictionary:
			_total_cost += inst.get("cost_usd", 0.0)

	# Apply anomaly penalty if active (set by anomaly dialog)
	if _anomaly_active:
		_total_cost *= (1.0 + _anomaly_penalty_pct / 100.0)

	total_cost = _total_cost

	# -- 2. TOTAL MASS --
	var _total_mass = (
		selected_bus.mass_kg
		+ selected_power.mass_kg
		+ selected_battery.mass_kg
		+ selected_comms.mass_kg
		+ selected_adcs.mass_kg
		+ selected_propulsion.mass_kg
	)

	for inst in instruments:
		if inst is Dictionary:
			_total_mass += inst.get("mass_kg", 0.0)

	total_mass = _total_mass

	# -- 3. POWER GENERATION (Inverse-Square Law) --
	# Solar panels output scales with 1/r^2; RTG is unaffected
	var is_rtg = selected_power.name.contains("RTG") or selected_power.name.contains("Hybrid")

	if is_rtg:
		# RTG output is constant (use usable_output_watts if RTG-only)
		raw_power_generation_watts = selected_power.usable_output_watts
	else:
		# Inverse-Square Law: power = base / (distance_au^2)
		# Solar_distance_au comes from selected_mission
		var base_output = selected_power.output_watts
		var dist_au = selected_mission.solar_distance_au
		raw_power_generation_watts = base_output / (dist_au * dist_au)

	# Apply reliability to usable output
	var usable_output = raw_power_generation_watts * selected_power.reliability_pct

	# -- 4. PEAK POWER LOAD --
	# Bus power draw + all instrument power draw
	var bus_power_draw = selected_bus.power_watts
	var instrument_power_draw = 0.0

	for inst in instruments:
		if inst is Dictionary:
			instrument_power_draw += inst.get("power_kw", 0.0) * 1000.0  # Convert kW to watts

	peak_power_load_watts = bus_power_draw + instrument_power_draw

	# -- 5. POWER MARGIN --
	power_margin_pct = ((usable_output - peak_power_load_watts) / usable_output) * 100.0

	# -- 6. ECLIPSE BATTERY DRAIN --
	# Load = peak_power_load_watts
	# Eclipse hours from mission
	# Drain = Load * eclipse_hours (amp*hours if load in watts, but power systems rate: w*h / v = Ah)
	# Assuming 28V bus: drain = peak_power_load_watts * eclipse_hours / 28.0
	var bus_voltage = 28.0
	eclipse_battery_drain_amp_hrs = peak_power_load_watts * selected_mission.eclipse_hours / bus_voltage

	# Usable battery capacity (80% typical)
	usable_battery_capacity_amp_hrs = selected_battery.capacity_ah * 0.8

	# -- 7. DATA CAPTURE RATIO --
	# Downlink capacity (Kom or selected_comms bandwidth)
	var downlink_capacity = selected_comms.bandwidth_gbps

	# Data generation (mission-based + instruments)
	var mission_data_gen = selected_mission.data_generation_gbps
	var instrument_data_gen = 0.0

	for inst in instruments:
		if inst is Dictionary:
			instrument_data_gen += inst.get("data_output_gbps", 0.0)

	var total_data_gen = mission_data_gen + instrument_data_gen
	data_capture_ratio = total_data_gen / downlink_capacity if downlink_capacity > 0.0 else 0.0

	# -- 8. EFFECTIVE SCIENCE YIELD --
	# Base science + instrument science - penalties
	# Anomaly penalty applies after calculation
	var base_science = selected_mission.science_yield
	var instrument_science_sum = 0.0

	for inst in instruments:
		if inst is Dictionary:
			instrument_science_sum += inst.get("science_points", 0.0)

	effective_science_yield = base_science + instrument_science_sum

	if _anomaly_active:
		effective_science_yield *= (1.0 + _anomaly_penalty_pct / 100.0)

	# -- 9. LIFETIME --
	# Simplified: based on bus life, RTG-specific, and reliability
	if is_rtg:
		lifetime_years = 12.0  # RTG typical
	else:
		lifetime_years = 5.0

	# -- 10. ALERTS --
	blockers.clear()
	warnings.clear()

	# Blockers (red): hard constraints
	# 1. Mass must not exceed launcher capacity (20% buffer)
	if total_mass > selected_launcher.mass_capacity_kg * 0.8:
		blockers.append({
			"type": "BLOCKER",
			"title": "Mass Overflow",
			"message": "Total mass (%.1f kg) exceeds mission budget by %.1f kg - reduce bus or instruments" % [total_mass, total_mass - selected_launcher.mass_capacity_kg]
		})

	# 2. Cost must not exceed mission budget + 20% (sandbox mode unlimited)
	if not _sandbox_mode and total_cost > selected_mission.budget_usd * 1.2:
		blockers.append({
			"type": "BLOCKER",
			"title": "Budget Overflow",
			"message": "Total cost (%.2f million) exceeds mission budget by %.1f%%" % [total_cost / 1_000_000, (total_cost - selected_mission.budget_usd) / selected_mission.budget_usd * 100.0]
		})

	# 3. Power margin must not be negative
	if power_margin_pct < 0.0:
		blockers.append({
			"type": "BLOCKER",
			"title": "Power Deficit",
			"message": "Peak power load (%.1f W) exceeds generation (%.1f W) by %.1f W - reduce instruments or use RTG" % [peak_power_load_watts, usable_output, usable_output - peak_power_load_watts]
		})

	# Warnings (yellow): soft constraints
	# 1. Low data capture ratio
	if data_capture_ratio < 0.7:
		warnings.append({
			"type": "WARNING",
			"title": "Low Data Downlink",
			"message": "Data capture at %.1f%% below mission target - consider higher bandwidth comms" % (data_capture_ratio * 100.0)
		})

	# 2. Low eclipse battery margin
	if eclipse_battery_drain_amp_hrs > usable_battery_capacity_amp_hrs * 0.9:
		warnings.append({
			"type": "WARNING",
			"title": "Eclipse Vulnerability",
			"message": "Eclipse drain (%.1f Ah) nearly reaches usable capacity (%.1f Ah) - add battery or RTG" % [eclipse_battery_drain_amp_hrs, usable_battery_capacity_amp_hrs]
		})

	# 3. Low power margin (but not blocker)
	if power_margin_pct < 30.0:
		warnings.append({
			"type": "WARNING",
			"title": "Tight Power Budget",
			"message": "Power margin at %.1f%% - consider RTG or reduce instrument load" % power_margin_pct
		})

	# Emit signal with all 6 metrics
	emit_signal("state_updated", {
		"budget_usd": total_cost,
		"mass_kg": total_mass,
		"power_watts": usable_output,
		"power_margin_pct": power_margin_pct,
		"data_capture_ratio": data_capture_ratio,
		"science_yield": effective_science_yield,
		"eclipse_drain_amp_hrs": eclipse_battery_drain_amp_hrs,
		"battery_capacity_amp_hrs": usable_battery_capacity_amp_hrs,
		"lifetime_years": lifetime_years
	})


# -- PROPERTY GETTERS --
func get_mission_title() -> String:
	return selected_mission.get("title", "Mission Pending")

func get_mission_description() -> String:
	return selected_mission.get("description", "")

func get_orbit_name() -> String:
	return selected_orbit.get("name", "Select Orbit")

func get_launcher_name() -> String:
	return selected_launcher.get("name", "Select Launcher")

func get_bus_name() -> String:
	return selected_bus.get("name", "Select Bus")

func is_sandbox_mode() -> bool:
	return _sandbox_mode

func get_instrument_count() -> int:
	return instruments.size()

# -- STATE WRITERS --
func set_selected_mission(mission_dict: Dictionary) -> void:
	selected_mission = mission_dict
	_recalculate_mission()


func set_selected_orbit(orbit_dict: Dictionary) -> void:
	selected_orbit = orbit_dict
	_recalculate_mission()


func set_selected_launcher(launcher_dict: Dictionary) -> void:
	selected_launcher = launcher_dict
	_recalculate_mission()


func set_selected_bus(bus_dict: Dictionary) -> void:
	selected_bus = bus_dict
	instruments = []  # Bus change invalidates instrument selections
	_recalculate_mission()


func set_instruments(inst_list: Array) -> void:
	instruments = inst_list
	_recalculate_mission()


func set_role_sign_off(role: String, signed: bool) -> void:
	if mission_role_sign_offs.has(role):
		mission_role_sign_offs[role] = signed
		_recalculate_mission()


func set_sandbox_mode(enabled: bool) -> void:
	_sandbox_mode = enabled
	_recalculate_mission()


# Anomaly handling (set by anomaly dialog)
func trigger_anomaly(penalty_pct: float) -> void:
	_anomaly_active = true
	_anomaly_penalty_pct = penalty_pct
	_recalculate_mission()


func clear_anomaly() -> void:
	_anomaly_active = false
	_anomaly_penalty_pct = 0.0
	_recalculate_mission()


func get_composite_score() -> int:
	# NASA 4 pillars: Objectives, Yield, Efficiency, Risk
	# Each pillar weighted equally (25%)
	var score_objectives: float = _calculate_objectives_score()
	var score_yield: float = _calculate_yield_score()
	var score_efficiency: float = _calculate_efficiency_score()
	var score_risk: float = _calculate_risk_score()

	var composite = ((score_objectives + score_yield + score_efficiency + score_risk) / 4.0) * 100.0

	# Clamp to 0-100 range
	composite = clamp(composite, 0.0, 100.0)

	return int(round(composite))


func _calculate_objectives_score() -> float:
	# Track % of mission objectives completed
	if selected_mission.is_empty():
		return 0.0

	# Simple logic: science_yield / max_possible (we don't have max, so use mission's yield as target)
	var target_science = float(selected_mission.science_yield)
	var current_science = effective_science_yield
	var ratio = current_science / target_science if target_science > 0.0 else 0.0

	return clamp(ratio * 100.0, 0.0, 100.0)


func _calculate_yield_score() -> float:
	# Downlink metrics: data capture ratio
	var ratio = clamp(data_capture_ratio, 0.0, 1.0)
	return ratio * 100.0


func _calculate_efficiency_score() -> float:
	# Balanced metric: (science_yield / cost) considering budget constraints
	var target_budget = float(selected_mission.budget_usd)

	# Penalize cost overruns harshly
	var cost_efficiency = 0.0
	if not _sandbox_mode and target_budget > 0.0:
		actual_cost = total_cost / 1_000_000.0  # Convert to millions
		if actual_cost > target_budget * 1.2:
			cost_efficiency = 0.0
		else:
			cost_efficiency = (effective_science_yield / actual_cost) if actual_cost > 0.0 else 0.0
	else:
		# Sandbox: lower efficiency due to no budget constraint
		cost_efficiency = (effective_science_yield / total_cost) if total_cost > 0.0 else 0.0

	return clamp(cost_efficiency, 0.0, 100.0)


func _calculate_risk_score() -> float:
	# Risk penalty factors: power margin, eclipse margin, blocker count
	var risk_penalty = 0.0

	# 1. Power margin penalty
	var power_ok = power_margin_pct >= 30.0 and power_margin_pct < 0.0
	if not power_ok:
		risk_penalty += 20.0  # 20% penalty for power issues

	# 2. Eclipse margin penalty
	var eclipse_ok = eclipse_battery_drain_amp_hrs <= usable_battery_capacity_amp_hrs * 0.9
	if not eclipse_ok:
		risk_penalty += 15.0  # 15% penalty

	# 3. Any blocker denies launch (risk = 0.0 if blocked)
	if not blockers.is_empty():
		risk_penalty = 100.0  # Blocking risk penalty is max

	# 4. Warnings reduce efficiency/risk slightly
	risk_penalty += warnings.size() * 5.0

	return clamp(100.0 - risk_penalty, 0.0, 100.0)
