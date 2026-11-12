"""Classify complete, aligned congress observations without game actions."""
import math
from tools.readiness_evidence import classify_readiness

def classify_modal_readiness(expected_turn, ui, scene, modals):
    def is_int(x):
        return isinstance(x, int) and not isinstance(x, bool)
    
    def is_finite_int(x):
        if not is_int(x):
            return False
        try:
            return math.isfinite(x)
        except OverflowError:
            return False

    # 1. Validate base inputs using existing logic to get base status
    base = classify_readiness(expected_turn, ui, scene)
    base_status = base['status']
    
    # 2. Validate modals structure and content
    if not isinstance(modals, list):
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modals_type"}
    
    if len(modals) != 3:
        return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modals_count"}
        
    allowed_contexts = {"WorldCongressPopup", "WorldCongressBetweenTurns", "WorldCongressIntro"}
    seen_contexts = set()
    
    for m in modals:
        if not isinstance(m, dict):
            return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modal_item_type"}
            
        # Check required keys
        required_keys = ['context', 'scope_key', 'local_player', 'turn', 'hidden']
        for k in required_keys:
            if k not in m:
                return {"status": "UNKNOWN", "qualified": False, "reason": "missing_modal_field"}
        
        # Validate context
        ctx = m['context']
        if not isinstance(ctx, str) or ctx not in allowed_contexts:
            return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modal_context"}
        if ctx in seen_contexts:
            return {"status": "UNKNOWN", "qualified": False, "reason": "duplicate_modal_context"}
        seen_contexts.add(ctx)
        
        # Validate scope_key
        if not isinstance(m['scope_key'], str) or not m['scope_key']:
            return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modal_scope"}
            
        # Validate local_player
        if not is_int(m['local_player']) or m['local_player'] != 0:
            return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modal_local_player"}
            
        # Validate turn
        if not is_finite_int(m['turn']) or m['turn'] < 0:
            return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modal_turn"}
            
        # Validate hidden
        if not isinstance(m['hidden'], bool):
            return {"status": "UNKNOWN", "qualified": False, "reason": "bad_modal_hidden"}
            
        # Validate all modal fields even if the base is malformed.
        if base_status == "UNKNOWN":
            continue

        # Validate alignment with UI and Scene
        if m['scope_key'] != ui['scope_key'] or m['scope_key'] != scene['scope_key']:
            return {"status": "UNKNOWN", "qualified": False, "reason": "modal_scope_misaligned"}
        if m['local_player'] != ui['local_player'] or m['local_player'] != scene['local_player']:
            return {"status": "UNKNOWN", "qualified": False, "reason": "modal_local_misaligned"}
        if m['turn'] != ui['turn'] or m['turn'] != scene['turn']:
            return {"status": "UNKNOWN", "qualified": False, "reason": "modal_turn_misaligned"}

    # 3. Determine final status based on priority
    # Priority: UNKNOWN/TURN_PASSED/NPC_BLOCKED from base are preserved if they are not READY/WAIT_AI
    # If base is READY or WAIT_AI, check for visible modals (hidden=False)
    
    if base_status in ("UNKNOWN", "TURN_PASSED", "NPC_BLOCKED"):
        return base
        
    # If base is READY or WAIT_AI, check modals
    # If any modal is visible (hidden is False), it blocks the turn
    for m in modals:
        if m['hidden'] is False:
            return {"status": "MODAL_BLOCKED", "qualified": False, "reason": "visible_world_congress"}
            
    # If no visible modals, return base status
    return base
