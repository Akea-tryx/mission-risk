extends Control

## Mission Risk: Main Dashboard Scene
## 3-column UI with live metrics HUD, OptionButton controls, SubViewport 3D, role sign-offs,
## anomaly dialog, and final report

@onready var hud_container: HBoxContainer = $HUDBar/HUDContainer
@onready var budget_label: Label = $HUDBar/HUDContainer/BudgetValue
@onready var mass_label: Label = $HUDBar/HUDContainer/MassValue
@onready var power_label: Label = $HUDBar/HUDContainer/PowerValue
@onready var data_label: Label = $HUDBar/HUDContainer/DataValue
@onready var science_label: Label = $HUDBar/HUDContainer/ScienceValue
@onready var lifetime_label: Label = $HUDBar/HUDContainer/LifetimeValue

@onready var mission_state: Node = get_node_or_null("/root/MissionState")
@onready var anomaly_confirm_dialog: AcceptDialog = $AnomalyConfirmDialog
@onready var final_report_dialog: AcceptDialog = $FinalReportDialog
@onready var logger: RichTextLabel = $MainLayout/RightCol/RisksTextLabel

# OptionButton controls
@onready var orbit_dropdown: OptionButton = $MainLayout/ControlsCol/OrbitDropdown
@onready var launcher_dropdown: OptionButton = $MainLayout/ControlsCol/LauncherDropdown
@onready var bus_dropdown: OptionButton = $MainLayout/ControlsCol/BusDropdown
@onready var power_dropdown: OptionButton = $MainLayout/ControlsCol/PowerDropdown
@onready var battery_dropdown: OptionButton = $MainLayout/ControlsCol/BatteryDropdown
@onready var comms_dropdown: OptionButton = $MainLayout/ControlsCol/CommsDropdown
@onready var adcs_dropdown: OptionButton = $MainLayout/ControlsCol/ADCSDropdown
@onready var propulsion_dropdown: OptionButton = $MainLayout/ControlsCol/PropulsionDropdown

# Instrument checkboxes
var instrument_checkboxes: Array = []

var _catalog: Dictionary = {}


func _ready() -> void:
	_load_catalog()
	_populate_options()
	_connect_signals()
	if mission_state:
		mission_state.state_updated.connect(_on_state_updated)
		mission_state.state_updated.connect(_update_risk_ledger)

	# Load instrument checkboxes
	instrument_checkboxes = [
		$MainLayout/ControlsCol/InstrumentContainer/InstrumentsCol/InstrumentList/InstCheckBox1,
		$MainLayout/ControlsCol/InstrumentContainer/InstrumentsCol/InstrumentList/InstCheckBox2,
		$MainLayout/ControlsCol/InstrumentContainer/InstrumentsCol/InstrumentList/InstCheckBox3,
		$MainLayout/ControlsCol/InstrumentContainer/InstrumentsCol/InstrumentList/InstCheckBox4,
	]

	# Connect instrument signals
	for checkbox in instrument_checkboxes:
		checkbox.toggled.connect(_on_instrument_toggled)

	# Connect role sign-off signals
	$MainLayout/RightCol/RoleSignOffSection/DirectorCheck.toggled.connect(_on_role_sign_off.bind("director"))
	$MainLayout/RightCol/RoleSignOffSection/ScientistCheck.toggled.connect(_on_role_sign_off.bind("scientist"))
	$MainLayout/RightCol/RoleSignOffSection/EngineerCheck.toggled.connect(_on_role_sign_off.bind("engineer"))
	$MainLayout/RightCol/RoleSignOffSection/CommsCheck.toggled.connect(_on_role_sign_off.bind("comms"))

	# Initial update
	_on_state_updated(_get_current_metrics())


func _load_catalog() -> void:
	if FileAccess.file_exists("res://data/catalog.json"):
		var file = FileAccess.open("res://data/catalog.json", FileAccess.READ)
		var json_res = JSON.parse_string(file.get_as_text())
		if json_res is Dictionary:
			_catalog = json_res
		file.close()


func _populate_options() -> void:
	_populate_dropdown(orbit_dropdown, _catalog.get("orbits", []), "id")
	_populate_dropdown(launcher_dropdown, _catalog.get("launch_vehicles", []), "id")
	_populate_dropdown(bus_dropdown, _catalog.get("buses", []), "id")
	_populate_dropdown(power_dropdown, _catalog.get("power", []), "id")
	_populate_dropdown(battery_dropdown, _catalog.get("batteries", []), "id")
	_populate_dropdown(comms_dropdown, _catalog.get("comms", []), "id")
	_populate_dropdown(adcs_dropdown, _catalog.get("adcs", []), "id")
	_populate_dropdown(propulsion_dropdown, _catalog.get("propulsion", []), "id")


func _populate_dropdown(button: OptionButton, items: Array, key: String) -> void:
	button.clear()
	button.add_item("--- Select ---")
	for item in items:
		button.add_item(str(dict_get(item, key)) + " - " + dict_get(item, "name"))


# Helper to safely get dict values
func dict_get(dict: Dictionary, key: String, default = "") -> Variant:
	return dict.get(key, default)


func _connect_signals() -> void:
	orbit_dropdown.item_selected.connect(_on_orbit_selected)
	launcher_dropdown.item_selected.connect(_on_launcher_selected)
	bus_dropdown.item_selected.connect(_on_bus_selected)
	power_dropdown.item_selected.connect(_on_power_selected)
	battery_dropdown.item_selected.connect(_on_battery_selected)
	comms_dropdown.item_selected.connect(_on_comms_selected)
	adcs_dropdown.item_selected.connect(_on_adcs_selected)
	propulsion_dropdown.item_selected.connect(_on_propulsion_selected)


func _process(delta: float) -> void:
	# Animate satellite orbit
	var satellite: MeshInstance3D = $MainLayout/ViewportCol/ViewportContainer/SubViewport/World/Satellite
	satellite.rotation.y += delta * 0.5

	# Animate orbit ring
	var orbit_ring: MeshInstance3D = $MainLayout/ViewportCol/ViewportContainer/SubViewport/World/OrbitRing
	orbit_ring.rotation.y += delta * 0.1


func _on_state_updated(metrics: Dictionary) -> void:
	_update_hud(metrics)

func _get_current_metrics() -> Dictionary:
	return {
		"budget_usd": mission_state.total_cost,
		"mass_kg": mission_state.total_mass,
		"power_watts": mission_state.effective_science_yield,
		"power_margin_pct": mission_state.power_margin_pct,
		"data_capture_ratio": mission_state.data_capture_ratio,
		"science_yield": mission_state.effective_science_yield,
		"eclipse_drain_amp_hrs": mission_state.eclipse_battery_drain_amp_hrs,
		"battery_capacity_amp_hrs": mission_state.usable_battery_capacity_amp_hrs,
		"lifetime_years": mission_state.lifetime_years
	}


func _update_hud(metrics: Dictionary) -> void:
	var budget_color = Color(1.0, 0.8, 0.0, 1)
	var mass_color = Color(1.0, 0.8, 0.0, 1)
	var power_color = Color(1.0, 0.8, 0.0, 1)

	if mission_state and mission_state.total_mass > mission_state.selected_launcher.get("mass_capacity_kg", 99999):
		mass_color = Color(1.0, 0.4, 0.4)
	if mission_state and mission_state.power_margin_pct < 0.0:
		power_color = Color.RED

	# Budget (millions)
	budget_label.text = "$%dM" % int(metrics.budget_usd / 1_000_000)

	# Mass
	mass_label.text = "%d kg" % int(metrics.mass_kg)
	mass_label.modulate = mass_color

	# Power (watts)
	power_label.text = "%.0f W" % metrics.power_watts

	# Data capture ratio
	var data_pct = metrics.data_capture_ratio * 100.0
	data_label.text = "%.1f%%" % data_pct

	# Science yield
	science_label.text = "%.0f" % metrics.science_yield

	# Lifetime
	lifetime_label.text = "%.1f yrs" % metrics.lifetime_years


func _update_risk_ledger(_metrics: Dictionary) -> void:
	var logger_text: String = ""

	# Blockers (red)
	for blocker in mission_state.blockers:
		logger_text += "[color=#FF4444]⚠ BLOCKER: %s[/color]\n%s\n\n" % [blocker["title"], blocker["message"]]

	# Warnings (yellow)
	for warning in mission_state.warnings:
		logger_text += "[color=#FFAA00]⚠ WARNING: %s[/color]\n%s\n\n" % [warning["title"], warning["message"]]

	logger.text = logger_text


# -- OPTION BUTTON HANDLERS --
func _on_orbit_selected(index: int) -> void:
	if index < 1:
		return
	var orbit_id = _get_selected_id(orbit_dropdown)
	var orbit = _find_item_by_id(_catalog.get("orbits", []), orbit_id)
	mission_state.set_selected_orbit(orbit)

func _on_launcher_selected(index: int) -> void:
	if index < 1:
		return
	var launcher_id = _get_selected_id(launcher_dropdown)
	var launcher = _find_item_by_id(_catalog.get("launch_vehicles", []), launcher_id)
	mission_state.set_selected_launcher(launcher)

func _on_bus_selected(index: int) -> void:
	if index < 1:
		return
	var bus_id = _get_selected_id(bus_dropdown)
	var bus = _find_item_by_id(_catalog.get("buses", []), bus_id)
	mission_state.set_selected_bus(bus)

func _on_power_selected(index: int) -> void:
	if index < 1:
		return
	var power_id = _get_selected_id(power_dropdown)
	var power = _find_item_by_id(_catalog.get("power", []), power_id)
	mission_state.set_power_selected(power)

func _on_battery_selected(index: int) -> void:
	if index < 1:
		return
	var bat_id = _get_selected_id(battery_dropdown)
	var bat = _find_item_by_id(_catalog.get("batteries", []), bat_id)
	mission_state.set_battery_selected(bat)

func _on_comms_selected(index: int) -> void:
	if index < 1:
		return
	var comms_id = _get_selected_id(comms_dropdown)
	var comms = _find_item_by_id(_catalog.get("comms", []), comms_id)
	mission_state.set_comms_selected(comms)

func _on_adcs_selected(index: int) -> void:
	if index < 1:
		return
	var adcs_id = _get_selected_id(adcs_dropdown)
	var adcs = _find_item_by_id(_catalog.get("adcs", []), adcs_id)
	mission_state.set_adcs_selected(adcs)

func _on_propulsion_selected(index: int) -> void:
	if index < 1:
		return
	var prop_id = _get_selected_id(propulsion_dropdown)
	var prop = _find_item_by_id(_catalog.get("propulsion", []), prop_id)
	mission_state.set_propulsion_selected(prop)


func _get_selected_id(button: OptionButton) -> String:
	return button.get_item_metadata(button.selected)

func _find_item_by_id(items: Array, item_id: String) -> Dictionary:
	for item in items:
		if str(item.get("id", "")) == item_id:
			return item
	return {}


# -- INSTRUMENT HANDLERS --
func _on_instrument_toggled(toggled: bool, checkbox: CheckBox = null) -> void:
	var index = instrument_checkboxes.find(checkbox)
	if index == -1:
		return

	var instruments = []
	for i in range(instrument_checkboxes.size()):
		if instrument_checkboxes[i].is_pressed():
			instruments.append(_catalog["instruments"][i])
			instruments[-1]["iskey"] = true  # Keep track of instrument references
			instruments[-1]["own"] = Callable(mission_state, "owns")  # Store bus ownership check

	mission_state.set_instruments(instruments)


# -- ROLE SIGN-OFF HANDLERS --
func _on_role_sign_off(role: String, signed: bool) -> void:
	mission_state.set_role_sign_off(role, signed)
	_update_launch_button()


func _update_launch_button() -> void:
	var launcher: Button = $MainLayout/RightCol/LaunchButton
	var all_signed = mission_state.mission_role_sign_offs.values().all(func(x): return x)
	var has_blockers = not mission_state.blockers.is_empty()

	launcher.disabled = has_blockers or not all_signed

	if launcher.disabled:
		launcher.modulate = Color(0.2, 0.2, 0.2, 1)
	else:
		launcher.modulate = Color(0.0, 0.8, 0.9, 1)


# -- LAUNCH SIMULATION HANDLERS --
func _on_launch_simulation_pressed() -> void:
	# Pause and generate random anomaly
	var anomalies = mission_state._narrative["anomalies"] as Array
	var random_anomaly = anomalies.pick_random()

	# Populate anomaly dialog
	$AnomalyConfirmDialog/AnomalyTitle.text = "⚠ " + random_anomaly["title"]
	$AnomalyConfirmDialog/AnomalyTelemetry.text = random_anomaly["telemetry_clue"]

	# Store anomaly data for callback
	_current_anomaly_penalty = random_anomaly["choices"][0].get("science_penalty_pct", 0)

	# Show dialog
	$AnomalyConfirmDialog.popup_centered()


var _current_anomaly_penalty: float = 0.0

func _on_anomaly_choice1_pressed() -> void:
	# Apply penalty
	mission_state.clear_anomaly()
	mission_state.trigger_anomaly(_current_anomaly_penalty)
	_launch_simulation()

func _on_anomaly_choice2_pressed() -> void:
	mission_state.clear_anomaly()
	mission_state.trigger_anomaly(_current_anomaly_penalty)
	_launch_simulation()

func _launch_simulation() -> void:
	# Hide anomaly dialog
	$AnomalyConfirmDialog.hide()

	# Calculate composite score
	var score = mission_state.get_composite_score()

	# Calculate pillar scores
	var obj_score = mission_state._calculate_objectives_score()
	var yield_score = mission_state._calculate_yield_score()
	var eff_score = mission_state._calculate_efficiency_score()
	var risk_score = mission_state._calculate_risk_score()

	# Display final report
	var final_report = $FinalReportDialog
	final_report.get_node("ScoreLabel").text = "COMPOSITE SCORE: %d/100" % score
	final_report.get_node("ObjectiveScore").text = "Objectives: %.0f/100" % obj_score
	final_report.get_node("YieldScore").text = "Yield: %.0f/100" % yield_score
	final_report.get_node("EfficiencyScore").text = "Efficiency: %.0f/100" % eff_score
	final_report.get_node("RiskScore").text = "Risk: %.0f/100" % risk_score

	# Mission summary
	var summary_vbox = final_report.get_node("FinalReportVBox")
	var summary = RichTextLabel.new()
	summary.text = "[color=#FFAA00]Mission Risk: Post-Mission Evaluation[/color]\n\n"
	summary.text += "[color=#8A8AA0]%s[/color]\n" % mission_state.get_mission_title()
	summary.text += "• Total Science Yield: [color=#FFFFFF]%d[/color] points\n" % int(mission_state.effective_science_yield)
	summary.text += "• Total Mass: [color=#FFFFFF]%d kg[/color]\n" % int(mission_state.total_mass)
	summary.text += "• Power Margin: [color=#FFFFFF]%.1f%%[/color]\n" % mission_state.power_margin_pct

	# Remove old summary if exists
	var old_summary = summary_vbox.get_node("MissionSummary")
	if old_summary:
		old_summary.queue_free()

	summary_vbox.add_child(summary)
	summary_vbox.move_child(summary, 6)

	# Generate build code
	var build_code = "MKR-" + str(randi() % 9000 + 1000) + "-" + String.chr(65 + randi() % 26)
	final_report.get_node("BuildCodeLabel").text = "Shuttle Code: " + build_code

	# Show final report
	final_report.popup_centered()


func _on_report_finished() -> void:
	# Return to boardroom (for replay)
	get_tree().change_scene_to_file("res://scenes/Boardroom.tscn")
