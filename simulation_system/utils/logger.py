"""
Colored and structured logging system for clear hackathon explainability.
"""
import time
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class _DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = _DummyColor()
    Style = _DummyColor()
    def init(*args, **kwargs):
        pass

class FleetLogger:
    ROBOT_COLORS = {
        "AMR-1": Fore.CYAN,
        "AMR-2": Fore.LIGHTRED_EX,
        "AMR-3": Fore.LIGHTGREEN_EX,
        "AMR-4": Fore.YELLOW,
        "AMR-5": Fore.LIGHTMAGENTA_EX,
        "AMR-6": Fore.LIGHTCYAN_EX,
        "SYSTEM": Fore.WHITE,
        "P2P": Fore.LIGHTMAGENTA_EX,
        "CONFLICT": Fore.LIGHTRED_EX,
        "TASK": Fore.LIGHTBLUE_EX,
        "METRICS": Fore.LIGHTYELLOW_EX
    }
    
    _events = []
    _listeners = []

    @classmethod
    def register_listener(cls, callback):
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def get_recent_events(cls, limit: int = 10):
        return cls._events[-limit:]

    @classmethod
    def _record_event(cls, tag: str, message: str, level: str = "INFO"):
        event = {
            "timestamp": cls._timestamp(),
            "time_raw": time.time(),
            "tag": tag,
            "message": message,
            "level": level
        }
        cls._events.append(event)
        if len(cls._events) > 100:
            cls._events.pop(0)
        for listener in cls._listeners:
            try:
                listener(event)
            except Exception:
                pass

    @staticmethod
    def _timestamp() -> str:
        return time.strftime("%H:%M:%S", time.localtime())

    @classmethod
    def info(cls, tag: str, message: str):
        color = cls.ROBOT_COLORS.get(tag, Fore.WHITE)
        cls._record_event(tag, message, "INFO")
        print(f"{Style.DIM}[{cls._timestamp()}]{Style.RESET_ALL} {color}[{tag}]{Style.RESET_ALL} {message}")

    @classmethod
    def highlight(cls, tag: str, message: str):
        color = cls.ROBOT_COLORS.get(tag, Fore.WHITE)
        cls._record_event(tag, message, "HIGHLIGHT")
        print(f"{Style.DIM}[{cls._timestamp()}]{Style.RESET_ALL} {color}{Style.BRIGHT}[{tag}] >>> {message}{Style.RESET_ALL}")

    @classmethod
    def conflict(cls, message: str):
        cls._record_event("CONFLICT", message, "CONFLICT")
        print(f"{Style.DIM}[{cls._timestamp()}]{Style.RESET_ALL} {Fore.RED}{Style.BRIGHT}[CONFLICT MANAGER] {message}{Style.RESET_ALL}")

    @classmethod
    def reservation(cls, message: str):
        cls._record_event("RESERVATION", message, "RESERVATION")
        print(f"{Style.DIM}[{cls._timestamp()}]{Style.RESET_ALL} {Fore.MAGENTA}{Style.BRIGHT}[RESERVATION]{Style.RESET_ALL} {message}")

    @classmethod
    def warning(cls, tag: str, message: str):
        color = cls.ROBOT_COLORS.get(tag, Fore.YELLOW)
        cls._record_event(tag, message, "WARNING")
        print(f"{Style.DIM}[{cls._timestamp()}]{Style.RESET_ALL} {color}[{tag}] {message}{Style.RESET_ALL}")

    @classmethod
    def warn(cls, tag: str, message: str):
        cls.warning(tag, message)

    @classmethod
    def banner(cls, title: str):
        bar = "=" * 60
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{bar}\n {title.center(58)}\n{bar}{Style.RESET_ALL}\n")
