class_name GameState
extends Node

signal state_updated

var mission_level: int = 1 # 1 = Easy, 2 = Medium, 3 = Hard
var credibility: int = 100
var sanctioned_budget: float = 80.0
var budget_spent: float = 0.0
var success_rate_pct: int = 0

var part_hull_tier: int = 0      # 0=None, 1=Min(+5%), 2=Rec(+25%), 3=Best(+50%)
var part_payload_tier: int = 0   # 0=None, 1=Min(+5%), 2=Rec(+25%), 3=Best(+50%)
var selected_lv_tier: int = 0    # 0=None, 1=Budget LV(25% risk), 2=Standard LV(15% risk), 3=Heavy LV(5% risk)
var selected_traj_tier: int = 0  # 0=None, 1=Best(10% risk), 2=Moderate(25% risk), 3=Risky(45% risk)

var budget_read: bool = false
var last_rng_roll: int = 0
var mission_passed: bool = false
var team_generation: int = 1

# Physics Backend Telemetry
var backend_connected: bool = false
var backend_telemetry: Dictionary = {}
var backend_cutoff_alt_km: float = 0.0
var backend_max_q_kpa: float = 0.0

func roll_feasible_budget() -> void:
	budget_spent = 0.0
	success_rate_pct = 0
	part_hull_tier = 0
	part_payload_tier = 0
	selected_lv_tier = 0
	selected_traj_tier = 0
	budget_read = true

	# Guarantees the random budget is always feasible for at least Minimum equipment + LV
	if mission_level == 1:
		sanctioned_budget = float(randi_range(65, 95))
	elif mission_level == 2:
		sanctioned_budget = float(randi_range(110, 145))
	else:
		sanctioned_budget = float(randi_range(165, 220))
	recalculate()

func get_cost_scale() -> float:
	if mission_level == 1:
		return 1.0
	elif mission_level == 2:
		return 1.5
	return 2.2

func recalculate() -> void:
	var scale: float = get_cost_scale()
	var cost: float = 0.0
	var rate: int = 0

	# Equipment Part 1: Spacecraft Bus & Power (+5%, +25%, +50%)
	if part_hull_tier == 1:
		cost += 8.0 * scale
		rate += 5
	elif part_hull_tier == 2:
		cost += 18.0 * scale
		rate += 25
	elif part_hull_tier == 3:
		cost += 30.0 * scale
		rate += 50

	# Equipment Part 2: Scientific Payload & Avionics (+5%, +25%, +50%)
	if part_payload_tier == 1:
		cost += 8.0 * scale
		rate += 5
	elif part_payload_tier == 2:
		cost += 18.0 * scale
		rate += 25
	elif part_payload_tier == 3:
		cost += 30.0 * scale
		rate += 50

	# Launch Vehicle (LV) Cost & LV Risk % Deduction (25%, 15%, 5%)
	if selected_lv_tier == 1:
		cost += 12.0 * scale
		rate -= 25
	elif selected_lv_tier == 2:
		cost += 22.0 * scale
		rate -= 15
	elif selected_lv_tier == 3:
		cost += 35.0 * scale
		rate -= 5

	# Head Scientist Trajectory Risk % Deduction (10%, 25%, 45%)
	if selected_traj_tier == 1:
		rate -= 10
	elif selected_traj_tier == 2:
		rate -= 25
	elif selected_traj_tier == 3:
		rate -= 45

	budget_spent = snapped(cost, 0.1)
	success_rate_pct = clamp(rate, 0, 99)
	state_updated.emit()

func remaining_budget() -> float:
	return snapped(sanctioned_budget - budget_spent, 0.1)
