class_name ApiClient
extends Node

## ApiClient: Handles HTTP network connectivity between Godot and the FastAPI Physics Backend.
## Communicates with http://127.0.0.1:8000/v1

const BASE_URL: String = "http://127.0.0.1:8000/v1"

signal health_checked(is_online: bool, data: Dictionary)
signal launch_completed(result: Dictionary)
signal mission_completed(result: Dictionary)
signal api_error(endpoint: String, message: String)

var is_backend_online: bool = false
var last_launch_result: Dictionary = {}
var last_mission_result: Dictionary = {}


func _ready() -> void:
	# Automatically check backend connectivity on startup
	check_health()


## Check if the physics backend server is running
func check_health() -> void:
	var http := HTTPRequest.new()
	add_child(http)
	http.timeout = 3.0

	http.request_completed.connect(func(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray):
		if response_code == 200:
			var json = JSON.parse_string(body.get_string_from_utf8())
			if json is Dictionary:
				is_backend_online = true
				GameState.backend_connected = true
				health_checked.emit(true, json)
				print("[ApiClient] Connected to Physics Backend: ", json)
				http.queue_free()
				return
		is_backend_online = false
		GameState.backend_connected = false
		health_checked.emit(false, {})
		http.queue_free()
	)

	var err = http.request(BASE_URL + "/health")
	if err != OK:
		is_backend_online = false
		GameState.backend_connected = false
		http.queue_free()


## Trigger an ascent trajectory simulation (POST /v1/launch/simulate)
func simulate_launch(kick_deg: float = 2.0, pitch2_deg: float = 30.0) -> void:
	var http := HTTPRequest.new()
	add_child(http)
	http.timeout = 10.0

	var payload = {
		"kick_deg": kick_deg,
		"pitch2_deg": pitch2_deg
	}
	var headers = ["Content-Type: application/json"]

	http.request_completed.connect(func(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray):
		if response_code == 200:
			var data = JSON.parse_string(body.get_string_from_utf8())
			if data is Dictionary:
				last_launch_result = data
				launch_completed.emit(data)
				_apply_launch_telemetry(data)
				http.queue_free()
				return
		var err_msg = body.get_string_from_utf8()
		api_error.emit("/launch/simulate", err_msg)
		http.queue_free()
	)

	var err = http.request(BASE_URL + "/launch/simulate", headers, HTTPClient.METHOD_POST, JSON.stringify(payload))
	if err != OK:
		api_error.emit("/launch/simulate", "HTTP request dispatch failed")
		http.queue_free()


## Trigger full end-to-end mission simulation (POST /v1/mission/simulate)
func simulate_mission(target_alt_m: float = 500000.0, beta_deg: float = 20.0) -> void:
	var http := HTTPRequest.new()
	add_child(http)
	http.timeout = 15.0

	var payload = {
		"target_alt_m": target_alt_m,
		"beta_deg": beta_deg
	}
	var headers = ["Content-Type: application/json"]

	http.request_completed.connect(func(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray):
		if response_code == 200:
			var data = JSON.parse_string(body.get_string_from_utf8())
			if data is Dictionary:
				last_mission_result = data
				mission_completed.emit(data)
				http.queue_free()
				return
		var err_msg = body.get_string_from_utf8()
		api_error.emit("/mission/simulate", err_msg)
		http.queue_free()
	)

	var err = http.request(BASE_URL + "/mission/simulate", headers, HTTPClient.METHOD_POST, JSON.stringify(payload))
	if err != OK:
		api_error.emit("/mission/simulate", "HTTP request dispatch failed")
		http.queue_free()


func _apply_launch_telemetry(data: Dictionary) -> void:
	var orb = data.get("orbit_at_cutoff", {})
	if orb is Dictionary:
		var bound: bool = orb.get("bound", false)
		var perigee_m: float = orb.get("perigee_alt_m", 0.0)
		var apogee_m: float = orb.get("apogee_alt_m", 0.0)
		var max_q: float = data.get("max_q_pa", 0.0)

		GameState.backend_cutoff_alt_km = perigee_m / 1000.0
		GameState.backend_max_q_kpa = max_q / 1000.0
		GameState.backend_telemetry = data

		# Physics-driven success check: orbit must be bound with perigee above 120 km
		if bound and perigee_m >= 120000.0:
			GameState.mission_passed = true
		else:
			GameState.mission_passed = false
		GameState.state_updated.emit()
