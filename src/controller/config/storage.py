"""
Wątkowo bezpieczny moduł zapisu/odczytu JSON dla Kontrolera Regis.
"""
import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

_file_locks: dict[str, threading.Lock] = {}
_global_lock = threading.Lock()


def _get_lock(filepath: Path | str) -> threading.Lock:
    """Pobiera lub tworzy dedykowaną blokadę wątkową dla konkretnej ścieżki pliku."""
    key = str(Path(filepath).resolve())
    with _global_lock:
        if key not in _file_locks:
            _file_locks[key] = threading.Lock()
        return _file_locks[key]


class JSONStorage:
    """Klasa pomocnicza zapewniająca wątkowo bezpieczny odczyt i atomowy zapis danych JSON."""

    @staticmethod
    def read_json(filepath: Path | str, default: Any = None) -> Any:
        """Bezpiecznie odczytuje plik JSON. Zwraca wartość domyślną, jeśli plik nie istnieje lub jest uszkodzony."""
        path = Path(filepath)
        lock = _get_lock(path)
        with lock:
            if not path.exists():
                return default if default is not None else {}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Błąd odczytu JSON z {path}: {e}")
                return default if default is not None else {}

    @staticmethod
    def write_json(filepath: Path | str, data: Any) -> None:
        """Atomowo zapisuje dane JSON z użyciem pliku tymczasowego (os.replace)."""
        path = Path(filepath)
        lock = _get_lock(path)
        with lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_fd, temp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
            try:
                with open(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(temp_path, path)
            except Exception as e:
                logging.error(f"Błąd atomowego zapisu JSON do {path}: {e}")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                raise e
