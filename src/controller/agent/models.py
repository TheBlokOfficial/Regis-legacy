"""
Modele LLM wspierane przez Regis Controller.
"""

SUPPORTED_REGIS_MODELS = [
    {
        "id": "qwen3.5:27b",
        "name": "Heavy Agent (Qwen 3.5 27B)",
        "description": "Zaawansowany model dużej mocy do złożonego rozumowania ReAct.",
        "default": False,
    },
    {
        "id": "qwen3.5:9b",
        "name": "Regis Agent (Qwen 3.5 9B)",
        "description": "Oficjalny, zalecany model produkcyjny z pełnym rozumowaniem ReAct.",
        "default": True,
    },
    {
        "id": "qwen2.5:32b",
        "name": "Heavy Agent (Qwen 2.5 32B)",
        "description": "Duży model 32B dla stacji roboczych GPU.",
        "default": False,
    },
    {
        "id": "qwen2.5:3b",
        "name": "Light Agent (Qwen 2.5 3B)",
        "description": "Szybki, lżejszy agent dla średnich komputerów.",
        "default": False,
    },
    {
        "id": "qwen2.5:0.5b",
        "name": "Butler NLU (Qwen 2.5 0.5B)",
        "description": "Kompaktowy parser komend dla słabych urządzeń.",
        "default": False,
    },
]
