extends Control

## Mission Risk: Boardroom Introduction Scene
## Displays boardroom dialogue, 3 mission dossiers, and initializes the mission

@onready var rich_text_label: RichTextLabel = $VBoxContainer/TitlePanel/DynamicDialogue/RichTextLabel
@onready var analyze_btn: Button = $VBoxContainer/TitlePanel/DynamicDialogue/ButtonPanel/AnalyzeBtn
@onready var initialize_btn: Button = $VBoxContainer/InitializeButton
@onready var mission_state: MissionState = get_node("/root/MissionState")

var _is_dialogue_complete: bool = false
var _current_index: int = 0


func _ready() -> void:
    _load_dialogue()
    reveal_animated()


func _process(delta: float) -> void:
    # Auto-advance dialogue
    if _is_dialogue_complete and Input.is_action_just_pressed("ui_accept"):
        on_analyze_pressed()


func _load_dialogue() -> void:
    if mission_state._narrative.has("boardroom_intro"):
        var dialogue_lines: Array = mission_state._narrative["boardroom_intro"] as Array

        # Format dialogue for display
        var formatted_text: String = ""
        for line in dialogue_lines:
            formatted_text += "[color=#8A8AA0]%s[/color]\n\n" % line.replace("\"", "")

        rich_text_label.text = formatted_text


func reveal_animated() -> void:
    # Simple fade-in effect for dialogue
    rich_text_label.modulate = Color(0.8, 0.8, 0.9, 0.0)
    var tween = create_tween()
    tween.tween_property(rich_text_label, "modulate:a", 1.0, 2.0)


func _on_analyze_pressed() -> void:
    _is_dialogue_complete = true
    analyze_btn.text = "BEGIN SIMULATION"
    analyze_btn.modulate = Color(0.0, 0.8, 0.9, 1)

    # Fade out dialogue
    var tween = create_tween()
    tween.tween_property(rich_text_label, "modulate:a", 0.0, 0.5)


func _on_initialize_pressed() -> void:
    # In a full implementation, this would read the selected mission from the UI
    # For now, we'll demonstrate with the first mission as a placeholder
    print("Initializing Mission Risk simulation...")

    # TODO: Load catalog.json to get mission data
    # var catalog = mission_state._catalog
    # var missions: Array = catalog.get("missions", [])

    # For now, use the Heliophysics mission as default
    var demo_mission = {
        "id": "m01",
        "title": "Heliophysics Mission",
        "budget_usd": 120000000,
        "mass_kg": 1200,
        "solar_distance_au": 1.02,
        "orbit": "LEO",
        "description": "Study solar flares and predict space weather events.",
        "science_yield": 850
    }

    mission_state.set_selected_mission(demo_mission)
    mission_state.set_sandbox_mode(false)

    # Change to main dashboard
    get_tree().change_scene_to_file("res://scenes/MainDashboard.tscn")