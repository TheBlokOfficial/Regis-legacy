import atexit
import os
import signal
import socket
import sys
import threading
import pystray

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from client import controller_api
from client.logger import setup_logging
from client.tray import create_default_icon, get_menu

app_tray: pystray.Icon | None = None
_instance_socket: socket.socket | None = None


def ensure_single_instance(port: int = 47829) -> None:
    """Sprawdza czy kolejna instancja Regis Satellite Daemon nie jest już uruchomiona w systemie."""
    global _instance_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.listen(1)
        _instance_socket = s
    except OSError:
        print("[Single Instance] Satelita Desktopowa Regis jest już uruchomiona w tle.")
        sys.exit(0)


def quit_all(icon=None) -> None:
    """Wyrejestrowuje klienta i zamyka aplikację Satelity w zasobniku."""
    controller_api.unregister()
    if app_tray:
        app_tray.stop()
    elif icon:
        icon.stop()
    os._exit(0)


_win_ctrl_handler = None

def setup_signal_handlers() -> None:
    """Podłącza sygnały wyjścia z systemu operacyjnego do funkcji wyjścia."""
    global _win_ctrl_handler
    atexit.register(quit_all)
    try:
        signal.signal(signal.SIGTERM, lambda signum, frame: quit_all())
        signal.signal(signal.SIGINT, lambda signum, frame: quit_all())
    except ValueError:
        pass

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
            
            def _win_handler(ctrl_type):
                quit_all()
                return True

            _win_ctrl_handler = PHANDLER_ROUTINE(_win_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_win_ctrl_handler, True)
        except Exception:
            pass


def main() -> None:
    """Główny punkt wejścia (Entry Point) aplikacji Satelity Desktopowej Regis."""
    global app_tray

    # 0. Zabezpieczenie przed podwójnym uruchomieniem
    ensure_single_instance()

    # 1. Inicjalizacja lokalna aplikacji i logowania
    setup_logging("client")
    setup_signal_handlers()

    # 2. Uruchomienie lokalnego proxy dla zdarzeń satelity
    from client.internal_proxy import start_internal_proxy_thread
    start_internal_proxy_thread()

    # 3. Uruchomienie stałego połączenia WebSocket z Kontrolerem
    ws_thread = threading.Thread(target=controller_api.start_ws_client, daemon=True)
    ws_thread.start()
    controller_api.wait_for_ws_connection(timeout=3.0)

    # 4. Uruchomienie silnika audio Satelity (VAD, WakeWord, Audio Player)
    from client.services.satellite.__main__ import start_satellite_thread
    start_satellite_thread()

    # 5. Uruchomienie pętli ikony w zasobniku systemowym (system tray)
    app_tray = pystray.Icon("regis_client", create_default_icon(), "Regis Satellite", menu=get_menu(quit_all))
    app_tray.run()


if __name__ == "__main__":
    main()
