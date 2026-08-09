import json

def build_messages_from_history(system_prompt: str, history: list[dict], current_message: str = None) -> list[dict]:
    """
    Odbudowuje listę wiadomości. Zakładamy, że history to już płaska lista obiektów {"role": ..., "content": ...}.
    """
    messages = [{"role": "system", "content": system_prompt}]
    
    # Klonujemy historię, wykluczając wewnętrzne pola używane tylko przez system (np. timestamp, elapsed_ms)
    for msg in history:
        clean_msg = {"role": msg["role"], "content": msg["content"]}
        if "tool_calls" in msg and msg["tool_calls"]:
            clean_msg["tool_calls"] = msg["tool_calls"]
        if "name" in msg:
            clean_msg["name"] = msg["name"]
        if "tool_call_id" in msg:
            clean_msg["tool_call_id"] = msg["tool_call_id"]
        messages.append(clean_msg)
            
    if current_message:
        messages.append({"role": "user", "content": current_message})
        
    return messages
