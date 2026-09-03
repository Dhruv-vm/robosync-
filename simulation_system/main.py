#!/usr/bin/env python3
"""
STERLEBOM / ROBOSYNC - Edge-AI Based Distributed Fleet Coordination for Autonomous Mobile Robots (AMRs)
SIH 2026 Internal Prototype Demonstration.
"""
import argparse
import sys
from warehouse.scenarios import ScenarioType
from simulation.simulation import FleetSimulation
from utils.logger import FleetLogger

def parse_args():
    parser = argparse.ArgumentParser(
        description="ROBOSYNC: Decentralized Multi-AMR Warehouse Fleet Simulation (SIH 2026)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  normal        : Standard multi-robot warehouse operations with distributed task auctioning
  blocked       : Dynamic blocked aisle scenario demonstrating onboard local A* re-routing
  intersection  : Spatial-temporal intersection conflict detection, negotiation, and waiting
  failure       : AMR hardware fault scenario demonstrating emergency task release & re-bidding

Interactive Keybindings (in PyBullet GUI):
  [N] Switch to Normal Scenario
  [B] Switch to Blocked Aisle Scenario
  [I] Switch to Intersection Conflict Scenario
  [F] Switch to Robot Failure Scenario
  [R] Reset Current Scenario
  [Q] Quit Simulation
        """
    )
    parser.add_argument(
        "-s", "--scenario",
        type=str,
        default="normal",
        choices=["normal", "deadlock", "blocked", "intersection", "failure", "six_amr"],
        help="Select demo scenario (default: normal)"
    )
    parser.add_argument(
        "-n", "--num-amrs",
        type=int,
        default=6,
        choices=[1, 2, 3, 4, 5, 6],
        help="Number of active AMRs in fleet (default: 6)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run headless without PyBullet GUI (for automated benchmark testing)"
    )
    parser.add_argument(
        "--no-debug",
        dest="visual_debug",
        action="store_false",
        default=True,
        help="Disable in-simulation 3D text billboards and HUD for maximum FPS"
    )
    parser.add_argument(
        "--visual-debug",
        dest="visual_debug",
        action="store_true",
        help="Enable in-simulation 3D text billboards and HUD (default)"
    )
    parser.add_argument(
        "--sim-speed",
        type=float,
        default=1.0,
        help="Simulation playback speed multiplier (e.g. 1.0 = real-time, 2.0 = 2x speed, 5.0 = 5x speed)"
    )
    parser.add_argument(
        "--web-dashboard",
        dest="web_dashboard",
        action="store_true",
        default=True,
        help="Enable background Web Telemetry Dashboard on http://localhost:8080 (default: enabled)"
    )
    parser.add_argument(
        "--no-web",
        dest="web_dashboard",
        action="store_false",
        help="Disable background Web Telemetry Dashboard"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional max runtime in seconds before auto-terminating"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    scenario_map = {
        "normal": ScenarioType.NORMAL,
        "deadlock": ScenarioType.DEADLOCK,
        "blocked": ScenarioType.BLOCKED,
        "intersection": ScenarioType.INTERSECTION,
        "failure": ScenarioType.FAILURE,
        "six_amr": ScenarioType.SIX_AMR
    }
    
    scenario = scenario_map[args.scenario]
    gui = not args.headless
    web_enabled = args.web_dashboard
    
    FleetLogger.banner("STERLEBOM / ROBOSYNC: DECENTRALIZED AMR FLEET COORDINATION")
    FleetLogger.info("System", f"Selected Scenario: {scenario.value.upper()}")
    FleetLogger.info("System", f"Active AMRs: {args.num_amrs} independent onboard agents")
    FleetLogger.info("System", f"PyBullet GUI Mode: {'ENABLED' if gui else 'DISABLED (HEADLESS)'}")
    FleetLogger.info("System", f"Simulation Speed: {args.sim_speed}x | Visual Debug: {args.visual_debug if gui else 'N/A'}")
    
    sim = FleetSimulation(
        scenario_type=scenario,
        gui=gui,
        num_amrs=args.num_amrs,
        visual_debug=args.visual_debug,
        sim_speed=args.sim_speed,
        web_dashboard=web_enabled
    )
    sim.run_loop(max_duration=args.duration)

if __name__ == "__main__":
    main()
