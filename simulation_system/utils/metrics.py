"""
Performance metrics collector and reporter for decentralized fleet benchmarks.
"""
import time
try:
    from colorama import Fore, Style
except ImportError:
    class _DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = _DummyColor()
    Style = _DummyColor()

class FleetMetrics:
    def __init__(self):
        self.start_time: float = time.time()
        self.tasks_completed: int = 0
        self.task_durations: List[float] = []
        self.distance_travelled: Dict[str, float] = {}
        self.collision_count: int = 0
        self.conflicts_detected: int = 0
        self.conflicts_resolved: int = 0
        self.deadlocks_detected: int = 0
        self.deadlocks_resolved: int = 0
        self.waiting_time_sec: float = 0.0
        self.replan_count: int = 0
        self.successful_reroutes: int = 0

    def record_distance(self, robot_id: str, meters: float):
        self.distance_travelled[robot_id] = self.distance_travelled.get(robot_id, 0.0) + meters

    def record_task_completed(self, duration: float):
        self.tasks_completed += 1
        self.task_durations.append(duration)

    def record_conflict(self, resolved: bool = True):
        self.conflicts_detected += 1
        if resolved:
            self.conflicts_resolved += 1

    def record_deadlock(self, resolved: bool = True):
        self.deadlocks_detected += 1
        if resolved:
            self.deadlocks_resolved += 1

    def record_replan(self, is_reroute: bool = False):
        self.replan_count += 1
        if is_reroute:
            self.successful_reroutes += 1

    def record_collision(self):
        self.collision_count += 1

    def record_wait_time(self, seconds: float):
        self.waiting_time_sec += seconds

    def print_summary(self):
        elapsed = time.time() - self.start_time
        avg_task_time = (sum(self.task_durations) / len(self.task_durations)) if self.task_durations else 0.0
        total_dist = sum(self.distance_travelled.values())

        print(f"\n{Fore.GREEN}{Style.BRIGHT}{'='*60}")
        print("   ROBOSYNC DECENTRALIZED FLEET PERFORMANCE BENCHMARK")
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f" Total Simulation Runtime : {elapsed:.1f} s")
        print(f" Tasks Completed          : {Fore.CYAN}{self.tasks_completed}{Style.RESET_ALL}")
        print(f" Average Task Time        : {avg_task_time:.2f} s")
        print(f" Total Distance Travelled : {total_dist:.1f} m")
        for rid, dist in sorted(self.distance_travelled.items()):
            print(f"   ├─ {rid:<8} : {dist:.1f} m")
        print(f" Intersection Conflicts   : {Fore.YELLOW}{self.conflicts_detected}{Style.RESET_ALL} (Resolved: {self.conflicts_resolved})")
        print(f" Deadlocks Resolved       : {Fore.CYAN}{self.deadlocks_resolved}{Style.RESET_ALL} (Detected: {self.deadlocks_detected})")
        print(f" Autonomous Replans       : {self.replan_count} (Dynamic Reroutes: {self.successful_reroutes})")
        print(f" Total Fleet Waiting Time : {self.waiting_time_sec:.1f} s")
        if self.collision_count == 0:
            print(f" Collision Safety         : {Fore.GREEN}{Style.BRIGHT}ZERO COLLISIONS (0) - PASSED PERFECTLY{Style.RESET_ALL}")
        else:
            print(f" Collision Safety         : {Fore.RED}{Style.BRIGHT}{self.collision_count} COLLISIONS DETECTED!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*60}\n{Style.RESET_ALL}")
