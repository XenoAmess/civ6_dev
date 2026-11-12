"""Classify aligned readonly observations; never grants permission for game actions."""
import math

def classify_readiness(expected_turn, ui, scene):
    def is_int(x):
        return isinstance(x, int) and not isinstance(x, bool)
    
    def is_finite_int(x):
        if not is_int(x):
            return False
        try:
            return math.isfinite(x)
        except OverflowError:
            return False

    # Validate expected_turn
    if not is_finite_int(expected_turn) or expected_turn < 0 or expected_turn > 100000:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_expected_turn"}

    # Validate ui structure
    if not isinstance(ui, dict):
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_ui_type"}
    
    ui_keys = ['scope_key', 'local_player', 'turn', 'active', 'allowed', 'busy', 'messages', 'can_end_turn']
    for k in ui_keys:
        if k not in ui:
            return {"status": "UNKNOWN", "qualified": False, "reason": "missing_ui_field"}
        
    if not isinstance(ui['scope_key'], str) or not ui['scope_key']:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_ui_scope"}
    if not is_int(ui['local_player']) or ui['local_player'] != 0:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_ui_local_player"}
    if not is_finite_int(ui['turn']) or ui['turn'] < 0:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_ui_turn"}
    
    for k in ['active', 'allowed', 'busy', 'messages', 'can_end_turn']:
        if not isinstance(ui[k], bool):
            return {"status": "UNKNOWN", "qualified": False, "reason": "bad_ui_bool"}

    # Validate scene structure
    if not isinstance(scene, dict):
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_scene_type"}
        
    scene_keys = ['scope_key', 'local_player', 'turn', 'hidden']
    for k in scene_keys:
        if k not in scene:
            return {"status": "UNKNOWN", "qualified": False, "reason": "missing_scene_field"}
            
    if not isinstance(scene['scope_key'], str) or not scene['scope_key']:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_scene_scope"}
    if not is_int(scene['local_player']) or scene['local_player'] != 0:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_scene_local_player"}
    if not is_finite_int(scene['turn']) or scene['turn'] < 0:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_scene_turn"}
    if not isinstance(scene['hidden'], bool):
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_scene_hidden"}

    # Alignment check
    if ui['scope_key'] != scene['scope_key'] or ui['turn'] != scene['turn'] or ui['local_player'] != scene['local_player']:
        return {"status": "UNKNOWN", "qualified": False, "reason": "scope_turn_misaligned"}

    # State classification
    if ui['turn'] > expected_turn:
        return {"status": "TURN_PASSED", "qualified": False, "reason": "turn_passed"}
    
    if ui['turn'] < expected_turn - 1:
        return {"status": "UNKNOWN", "qualified": False, "reason": "old_archive"}
        
    # Same scope/turn verified
    if not scene['hidden']:
        return {"status": "NPC_BLOCKED", "qualified": False, "reason": "npc_display"}
        
    if scene['hidden'] and ui['turn'] == expected_turn and ui['active'] and ui['allowed'] and not ui['busy'] and not ui['messages']:
        return {"status": "READY", "qualified": True, "reason": "ready"}
        
    return {"status": "WAIT_AI", "qualified": False, "reason": "wait_ai"}
