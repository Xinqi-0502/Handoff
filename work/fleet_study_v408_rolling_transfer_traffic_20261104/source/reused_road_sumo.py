"""Live, simulation-only SUMO road backend for the door-to-door event engine.

The single truck persists in one SUMO process across every road leg. Native
car-following, finite lanes, junction right-of-way and traffic lights determine
movement; this module never multiplies a nominal trip time by a congestion
factor. Depot/merchant service occurs in native off-road parking areas. The
event engine must wait for road_leg_arrived, then perform pickup/handoff service.

Only current realized road observations and static network geometry are public.
The generated background-demand trace is saved for auditing but not exposed by
snapshot/public_model. This is a synthetic grid, not field traffic calibration.
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET


MODEL_VERSION = "live-sumo-persistent-truck-v1"
DEFAULT_PROJECT = Path(r"D:\traffic-coop-research")
EPS = 1e-7
DEPOT_ID = "depot"


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)


def _xml(path, root):
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be a finite number")
    if value < 0 or (positive and value <= 0):
        raise ValueError(name + " must be positive" if positive else name + " must be nonnegative")
    return float(value)


def discover_runtime(project_dir=DEFAULT_PROJECT):
    """Reuse the installed runtime read-only; never install or modify packages."""
    project = Path(project_dir).resolve()
    packages = project / ".venv" / "Lib" / "site-packages"
    if str(packages) not in sys.path:
        sys.path.append(str(packages))
    old_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        traci = importlib.import_module("traci")
        sumolib = importlib.import_module("sumolib")
        sumo = importlib.import_module("sumo")
    finally:
        sys.dont_write_bytecode = old_bytecode
    binary = Path(sumo.__file__).parent / "bin" / ("sumo.exe" if os.name == "nt" else "sumo")
    netconvert = binary.with_name("netconvert.exe" if os.name == "nt" else "netconvert")
    if not binary.is_file() or not netconvert.is_file():
        raise FileNotFoundError("The existing SUMO and netconvert runtime is required")
    return traci, sumolib, {"project_dir": str(project), "python": sys.executable,
                            "python_version": platform.python_version(), "sumo_binary": str(binary),
                            "netconvert_binary": str(netconvert),
                            "packages": {name: importlib.metadata.version(name)
                                         for name in ("eclipse-sumo", "traci", "sumolib")},
                            "sumo_version_text": subprocess.check_output([str(binary), "--version"], text=True),
                            "binary_sha256": {"sumo": _hash(binary), "netconvert": _hash(netconvert)}}


def diagnostic_counts(rows):
    """Count raw per-tick diagnostics; event and involved-ID counts are distinct."""
    return {"collision_event_count": sum(len(r.get("collisions", [])) for r in rows),
            "colliding_vehicle_tick_count": sum(len(r.get("colliding_vehicle_ids", [])) for r in rows),
            "teleport_started_count": sum(len(r.get("teleport_started_ids", [])) for r in rows),
            "teleport_ended_count": sum(len(r.get("teleport_ended_ids", [])) for r in rows)}


class SumoRoadBackend:
    """One live SUMO process and one persistent truck, advancing on road ticks.

    start_leg may be called between road ticks. Such a command is queued until
    the first road state time >= its request time, so travel cannot occur before
    dispatch. advance_to accepts only fixed tick boundaries. The caller must
    advance background traffic even when the truck is parked or serving orders.
    """
    def __init__(self, road_config, merchants, truck, seed, run_dir):
        self.config = copy.deepcopy(road_config or {})
        self.merchants = copy.deepcopy(merchants)
        self.truck_config = copy.deepcopy(truck)
        self.seed = int(seed)
        self.tick_s = _finite(self.config.get("tick_s", .5), "road.tick_s", positive=True)
        self.now_s = 0.0
        self.next_tick_s = self.tick_s
        self.path = Path(run_dir).resolve()
        self.path.mkdir(parents=True, exist_ok=False)
        self.connection = None
        self.console = None
        self.closed = False
        self.active_leg = None
        self.pending_leg = None
        self.legs = []
        self.current_anchor = DEPOT_ID
        self.raw_diagnostics = []
        self.background_departed = set()
        self.background_arrived = set()
        self.truck_id = str(truck["id"])
        self._last_observation = None
        self.distance_m = 0.0
        self._native_odometer = None
        self.max_queue_count = 0
        self.queue_vehicle_seconds = 0.0
        self.truck_waiting_tick_s = 0.0
        self.failure = None
        self._streams = {}
        for name in ("road_events.jsonl", "road_states.jsonl", "road_diagnostics.jsonl"):
            self._streams[name] = (self.path / name).open("x", encoding="utf-8")
        try:
            # This runtime represents native simulation time in milliseconds.
            # Reject fractional-millisecond steps before any SUMO process is
            # launched; otherwise e.g. .0625 silently becomes .063 and also
            # changes the supposedly fixed driver reaction step.
            if not math.isclose(self.tick_s * 1000, round(self.tick_s * 1000), abs_tol=EPS):
                raise ValueError("road.tick_s must be exactly representable in native integer milliseconds")
            self.traci, self.sumolib, self.runtime = discover_runtime(self.config.get("reuse_project_dir", DEFAULT_PROJECT))
            self._prepare()
            self._start()
        except BaseException:
            self.failure = traceback.format_exc()
            (self.path / "initialization_error.txt").write_text(self.failure, encoding="utf-8")
            self.finalize(0.0)
            raise

    def _emit(self, name, row):
        self._streams[name].write(_json(row) + "\n")
        self._streams[name].flush()

    def _event(self, event_type, **fields):
        row = {"event_type": event_type, "sim_s": self.now_s, **fields}
        self._emit("road_events.jsonl", row)
        return row

    def _prepare(self):
        if self.truck_id.startswith("BG_"):
            raise ValueError("Truck ID must not use the reserved BG_ prefix")
        self.truck_max_speed = _finite(self.truck_config["speed_m_s"], "truck.speed_m_s", positive=True)
        self.driver_action_step_s = _finite(self.config.get("driver_action_step_s", 1.0), "driver_action_step_s", positive=True)
        ratio = self.driver_action_step_s / self.tick_s
        if ratio < 1 - EPS or not math.isclose(ratio, round(ratio), abs_tol=EPS):
            raise ValueError("driver_action_step_s must be an integer multiple of tick_s and >= tick_s")
        self.scenario = self.path / "scenario"
        self.scenario.mkdir()
        source = Path(self.runtime["project_dir"]) / "src" / "traffic_lab"
        frozen = self.path / "reused_source"
        frozen.mkdir()
        self.reused_sources = {}
        for name in ("__init__.py", "fleet_map.py", "scenario.py", "domain.py"):
            original = source / name
            (frozen / name).write_bytes(original.read_bytes())
            self.reused_sources[str(original)] = _hash(original)
        # Avoid accidental writes of bytecode into the source project.
        old_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(source.parent))
        try:
            builder = importlib.import_module("traffic_lab.fleet_map")
            self.metadata = builder.build_fleet_map(self.scenario, "road", self.seed)
        finally:
            sys.dont_write_bytecode = old_bytecode
            sys.path.remove(str(source.parent))
        self.net = self.sumolib.net.readNet(str(self.scenario / "fleet.net.xml"), withInternal=True)
        ids = [m["id"] for m in self.merchants]
        if len(ids) != len(set(ids)) or DEPOT_ID in ids or len(ids) > 10:
            raise ValueError("Road anchors require unique merchant IDs, no reserved depot ID, and <=10 merchants")
        mapping = {DEPOT_ID: "X0", **{mid: f"S{index}" for index, mid in enumerate(ids)}}
        mapping.update(self.config.get("anchor_stations", {}))
        if set(mapping) != {DEPOT_ID, *ids} or len(set(mapping.values())) != len(mapping):
            raise ValueError("Anchor station mapping must cover exactly depot and merchants with distinct stations")
        self.anchors = {}
        for aid, station_id in mapping.items():
            if station_id not in self.metadata["stations"]:
                raise ValueError("Unknown network anchor station: " + str(station_id))
            station = self.metadata["stations"][station_id]
            edge = self.metadata["edges"][station["edge"]]
            lane = self.net.getLane(edge["lane"])
            pos = station["pos"]
            xy = self.sumolib.geomhelper.positionAtShapeOffset(lane.getShape(), pos)
            self.anchors[aid] = {"id": aid, "station_id": station_id, "edge": station["edge"],
                                 "lane": edge["lane"], "lane_index": edge["lane_index"],
                                 "position_m": pos, "x": xy[0], "y": xy[1]}
        self._make_parking()
        self._make_demand()
        self.geometry = {a: {b: self._static_route(a, b) for b in self.anchors} for a in self.anchors}
        self.public_model = {"model_version": MODEL_VERSION, "simulation_only": True,
                             "tick_s": self.tick_s, "depot_id": DEPOT_ID, "anchors": copy.deepcopy(self.anchors),
                             "anchor_matrix": copy.deepcopy(self.geometry),
                             "truck_max_speed_m_s": self.truck_max_speed,
                             "driver_action_step_s": self.driver_action_step_s,
                             "road_model": "Native SUMO finite lanes, car-following, junction right-of-way and fixed traffic lights",
                             "nominal_time_definition": "Static route speed-limit lower bound; excludes acceleration, signals, insertion, parking and endogenous queues; never an actual arrival timer",
                             "source_xy_semantics": "Merchant input x/y retained in input.json; explicitly mapped to synthetic road anchors shown here",
                             "pedestrians_included": False,
                             "scope": "Synthetic uncalibrated grid. No actual vendor adapter or real traffic observations."}
        _save(self.path / "public_model.json", self.public_model)
        _save(self.path / "input.json", {"road_config": self.config, "merchants": self.merchants,
                                         "truck": self.truck_config, "seed": self.seed})
        self._make_config()

    def _make_parking(self):
        additional = ET.Element("additional")
        for anchor in self.anchors.values():
            ET.SubElement(additional, "parkingArea", id=anchor["station_id"], lane=anchor["lane"],
                          startPos=str(anchor["position_m"] - 12), endPos=str(anchor["position_m"]),
                          roadsideCapacity="1", onRoad="false")
        _xml(self.scenario / "road_stations.add.xml", additional)

    def _make_demand(self):
        count = self.config.get("background_count", 120)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("background_count must be a nonnegative integer")
        demand_end = _finite(self.config.get("background_end_s", 600), "background_end_s", positive=True)
        begin = _finite(self.config.get("background_start_s", 0), "background_start_s")
        if begin > demand_end:
            raise ValueError("Background start must not exceed background end")
        rng = random.Random(self.seed + 108731)
        routes = ET.Element("routes")
        ET.SubElement(routes, "vType", id="road_truck", vClass="passenger", length="5", width="2",
                      accel="1.5", decel="4.5", emergencyDecel="7.5", tau="1.2", minGap="2.5",
                      actionStepLength=str(self.driver_action_step_s),
                      sigma="0", speedFactor="1", speedDev="0", maxSpeed=str(self.truck_max_speed))
        ET.SubElement(routes, "vType", id="road_background", vClass="passenger", length="4.5", width="1.8",
                      accel="1.3", decel="4.5", emergencyDecel="7.5", tau="1.2", minGap="2.5",
                      actionStepLength=str(self.driver_action_step_s),
                      sigma="0", speedFactor="1", speedDev="0", maxSpeed="8")
        edges = sorted(self.metadata["edges"])
        mode = self.config.get("background_mode", "random_pairs")
        if mode not in {"random_pairs", "bottleneck"}:
            raise ValueError("background_mode must be random_pairs or bottleneck")
        self.background = []
        for index in range(count):
            if mode == "bottleneck":
                source = self.config.get("bottleneck_from_edge", "N00_N10")
                target = self.config.get("bottleneck_to_edge", "N10_N11")
            else:
                source, target = rng.sample(edges, 2)
            path, _ = self.net.getShortestPath(self.net.getEdge(source), self.net.getEdge(target), vClass="passenger")
            if not path:
                raise ValueError("Background trip has no native legal route")
            departure = begin + (demand_end - begin) * index / max(1, count)
            vid = f"BG_{index:06d}"
            vehicle = ET.SubElement(routes, "vehicle", id=vid, type="road_background", depart=str(departure),
                                    departLane="1", departPos="base", departSpeed="0")
            route_edges = [edge.getID() for edge in path if edge.getFunction() == ""]
            ET.SubElement(vehicle, "route", edges=" ".join(route_edges))
            self.background.append({"id": vid, "requested_departure_s": departure, "route_edges": route_edges})
        _xml(self.scenario / "road_background.rou.xml", routes)
        _save(self.path / "background_demand.json", self.background)

    def _static_route(self, source, target):
        if source == target:
            return {"route_edges": [self.anchors[source]["edge"]], "distance_m": 0.0, "free_flow_s": 0.0}
        a, b = self.anchors[source], self.anchors[target]
        path, distance = self.net.getShortestPath(self.net.getEdge(a["edge"]), self.net.getEdge(b["edge"]),
                                                  vClass="passenger", withInternal=True,
                                                  fromPos=a["position_m"], toPos=b["position_m"])
        if not path:
            raise ValueError(f"Unreachable anchor pair {source} -> {target}")
        nominal = 0.0
        for index, edge in enumerate(path):
            length = edge.getLength()
            if index == 0:
                length -= a["position_m"]
            if index == len(path) - 1:
                length -= edge.getLength() - b["position_m"]
            nominal += max(0, length) / min(edge.getSpeed(), self.truck_max_speed)
        return {"route_edges": [edge.getID() for edge in path if edge.getFunction() == ""],
                "distance_m": distance, "free_flow_s": nominal}

    def road_geometry(self):
        return copy.deepcopy(self.public_model)

    def _make_config(self):
        cfg = ET.Element("configuration")
        sections = {
            "input": {"net-file": str(self.scenario / "fleet.net.xml"),
                      "route-files": str(self.scenario / "road_background.rou.xml"),
                      "additional-files": str(self.scenario / "road_stations.add.xml")},
            "time": {"begin": 0, "step-length": self.tick_s},
            "random_number": {"seed": self.seed % (2 ** 31)},
            "processing": {"time-to-teleport": -1, "collision.action": "warn",
                           "collision.check-junctions": "true", "collision.mingap-factor": 0,
                           "step-method.ballistic": "true"},
            "report": {"no-step-log": "true", "duration-log.disable": "true",
                       "log": str(self.path / "sumo.log"), "error-log": str(self.path / "sumo_errors.log")},
            "output": {"tripinfo-output": str(self.path / "tripinfo.xml"),
                       "tripinfo-output.write-unfinished": "true", "tripinfo-output.write-undeparted": "true",
                       "collision-output": str(self.path / "collisions.xml"),
                       "vehroute-output": str(self.path / "vehroute.xml"),
                       "vehroute-output.write-unfinished": "true", "vehroute-output.exit-times": "true"}}
        for section, values in sections.items():
            group = ET.SubElement(cfg, section)
            for key, value in values.items():
                ET.SubElement(group, key, value=str(value))
        self.cfg_path = self.path / "road.sumocfg"
        _xml(self.cfg_path, cfg)

    def _start(self):
        self.command = [self.runtime["sumo_binary"], "-c", str(self.cfg_path)]
        self.console = (self.path / "sumo_console.log").open("x", encoding="utf-8")
        label = "door-to-door-road-" + str(time.time_ns())
        self.traci.start(self.command, label=label, stdout=self.console, verbose=False, numRetries=5)
        self.connection = self.traci.getConnection(label)
        self.now_s = self.connection.simulation.getTime()
        if abs(self.now_s) > EPS:
            raise RuntimeError("Road backend must initialize at time zero without stepping future truth")
        anchor = self.anchors[DEPOT_ID]
        self.connection.route.add("persistent_truck_initial", [anchor["edge"]])
        self.connection.vehicle.add(self.truck_id, "persistent_truck_initial", typeID="road_truck",
                                    depart="now", departLane=str(anchor["lane_index"]),
                                    departPos=str(anchor["position_m"] - 6), departSpeed="0")
        self.connection.vehicle.setParkingAreaStop(self.truck_id, anchor["station_id"], duration=1e9)
        self.native_version = list(self.connection.getVersion())
        self.manifest = {"model_version": MODEL_VERSION, "runtime": self.runtime, "traci_version": self.native_version,
                         "seed": self.seed, "sumo_seed": self.seed % (2 ** 31), "command": self.command,
                         "connection": "TraCI client connects only to localhost; no external service",
                         "source_sha256": _hash(__file__), "reused_source_sha256": self.reused_sources,
                         "input_sha256": _hash(self.path / "input.json"),
                         "config_sha256": _hash(self.cfg_path),
                         "scenario_sha256": {p.name: _hash(p) for p in self.scenario.iterdir() if p.is_file()},
                         "actual_input_files": [str(self.scenario / n) for n in
                                                ("fleet.net.xml", "road_background.rou.xml", "road_stations.add.xml")],
                         "map_generator_unused_artifacts": "Generated historical background.rou.xml/demand.json include pedestrians but are NOT loaded. Actual native demand is road_background.rou.xml only.",
                         "claims": "Live native synthetic road dynamics, no field calibration or published algorithm reproduction",
                         "teleport_policy": "time-to-teleport=-1 prevents automatic jam teleport; diagnostics are still collected each tick",
                         "truck_identity_policy": "Single persistent native vehicle; no per-leg remove/reinsert, moveTo or speed override"}
        _save(self.path / "manifest.json", self.manifest)
        self._event("road_started", truck_id=self.truck_id, native_time_s=self.now_s,
                    initial_insertion_pending=True, simulation_only=True)

    def start_leg(self, now_s, destination_id, leg_id):
        now_s = _finite(now_s, "start_leg.now_s")
        if self.closed or self.active_leg is not None or self.pending_leg is not None:
            raise RuntimeError("Cannot dispatch a closed or already traveling persistent truck")
        if now_s + EPS < self.now_s or now_s >= self.next_tick_s + EPS:
            raise ValueError("Dispatch clock must be between the current and next road tick")
        if destination_id not in self.anchors:
            raise ValueError("Unknown road destination " + str(destination_id))
        leg = {"leg_id": str(leg_id), "source_id": self.current_anchor, "destination_id": destination_id,
               "requested_sim_s": now_s, "native_started_sim_s": None, "arrived_sim_s": None,
               "distance_m": None, "status": "pending", "distance_start_m": None,
               "nominal": copy.deepcopy(self.geometry[self.current_anchor][destination_id])}
        self.pending_leg = leg
        self.legs.append(leg)
        self._event("road_leg_requested", request_sim_s=now_s, leg_id=leg["leg_id"], source_id=self.current_anchor,
                    destination_id=destination_id, nominal=copy.deepcopy(leg["nominal"]))
        return {"leg_id": leg["leg_id"], "source_id": leg["source_id"], "destination_id": destination_id,
                "distance_m": leg["nominal"]["distance_m"], "free_flow_s": leg["nominal"]["free_flow_s"],
                "actual_arrived_sim_s": None}

    def _apply_pending(self):
        leg = self.pending_leg
        if leg is None or leg["requested_sim_s"] > self.now_s + EPS:
            return
        c = self.connection
        # The initial native insertion is allowed to occur only at a road tick;
        # before that the vehicle is not yet queryable or physically stopped.
        if self.truck_id not in c.vehicle.getIDList():
            return
        if not c.vehicle.isStoppedParking(self.truck_id):
            return
        if leg["destination_id"] == self.current_anchor:
            leg.update(native_started_sim_s=self.now_s, distance_start_m=self.distance_m, status="traveling")
            self.pending_leg, self.active_leg = None, leg
            return
        origin_edge = c.vehicle.getRoadID(self.truck_id)
        destination = self.anchors[leg["destination_id"]]
        path, _ = self.net.getShortestPath(self.net.getEdge(origin_edge), self.net.getEdge(destination["edge"]),
                                          vClass="passenger", fromPos=c.vehicle.getLanePosition(self.truck_id),
                                          toPos=destination["position_m"])
        if not path:
            raise RuntimeError("Persistent truck has no legal path to destination")
        route = [edge.getID() for edge in path if edge.getFunction() == ""]
        c.vehicle.resume(self.truck_id)
        for _ in range(len(c.vehicle.getStops(self.truck_id))):
            c.vehicle.replaceStop(self.truck_id, 0, "")
        c.vehicle.setRoute(self.truck_id, route)
        c.vehicle.setParkingAreaStop(self.truck_id, destination["station_id"], duration=1e9)
        # SUMO may retain the already traveled prefix after changing a route
        # while parked. The remaining route, starting at routeIndex, must match.
        readback = list(c.vehicle.getRoute(self.truck_id))[c.vehicle.getRouteIndex(self.truck_id):]
        if readback != route:
            raise RuntimeError(f"Native route readback differs from committed route: sent={route}, remaining={readback}")
        leg.update(native_started_sim_s=self.now_s, distance_start_m=self.distance_m,
                   status="traveling", actual_route_edges=route)
        self.pending_leg, self.active_leg = None, leg
        self._event("road_leg_native_started", leg_id=leg["leg_id"], request_sim_s=leg["requested_sim_s"],
                    native_started_sim_s=self.now_s, distance_start_m=self.distance_m,
                    route_edges=route, persistent_truck_id=self.truck_id)

    def advance_to(self, tick_sim_s):
        tick_sim_s = _finite(tick_sim_s, "road tick time")
        if self.closed:
            raise RuntimeError("Road backend is closed")
        count = round(tick_sim_s / self.tick_s)
        if not math.isclose(tick_sim_s, count * self.tick_s, abs_tol=EPS) or tick_sim_s < self.now_s - EPS:
            raise ValueError("Road may advance only to monotone fixed tick boundaries")
        returned = []
        try:
            while self.now_s + EPS < tick_sim_s:
                self._apply_pending()
                next_time = (round(self.now_s / self.tick_s) + 1) * self.tick_s
                self.connection.simulationStep(next_time)
                self.now_s = self.connection.simulation.getTime()
                if not math.isclose(self.now_s, next_time, abs_tol=EPS):
                    raise RuntimeError(f"Native SUMO clock mismatch: requested={next_time}, observed={self.now_s}")
                self.next_tick_s = (round(self.now_s / self.tick_s) + 1) * self.tick_s
                self._collect_tick()
                if self.active_leg is not None and self._at_target(self.active_leg["destination_id"]):
                    leg = self.active_leg
                    leg.update(arrived_sim_s=self.now_s, distance_m=max(0, self.distance_m - leg["distance_start_m"]),
                               duration_sim_s=self.now_s - leg["requested_sim_s"], status="arrived")
                    self.current_anchor = leg["destination_id"]
                    self.active_leg = None
                    returned.append(self._event("road_leg_arrived", leg_id=leg["leg_id"],
                                               destination_id=leg["destination_id"], arrived_sim_s=self.now_s,
                                               actual_arrived_sim_s=self.now_s, distance_m=leg["distance_m"],
                                               actual_distance_m=leg["distance_m"], duration_sim_s=leg["duration_sim_s"],
                                               request_sim_s=leg["requested_sim_s"], native_started_sim_s=leg["native_started_sim_s"],
                                               persistent_truck_id=self.truck_id))
                self._apply_pending()
            return returned
        except BaseException:
            self.failure = traceback.format_exc()
            (self.path / "execution_error.txt").write_text(self.failure, encoding="utf-8")
            raise

    def _at_target(self, destination_id):
        if self.truck_id not in self.connection.vehicle.getIDList():
            return False
        stops = self.connection.vehicle.getStops(self.truck_id)
        return bool(self.connection.vehicle.isStoppedParking(self.truck_id) and stops and
                    stops[0].stoppingPlaceID == self.anchors[destination_id]["station_id"])

    def _collect_tick(self):
        c = self.connection
        vehicles = list(c.vehicle.getIDList())
        departed, arrived = list(c.simulation.getDepartedIDList()), list(c.simulation.getArrivedIDList())
        self.background_departed.update(v for v in departed if v.startswith("BG_"))
        self.background_arrived.update(v for v in arrived if v.startswith("BG_"))
        collisions = []
        for collision in c.simulation.getCollisions():
            collisions.append({key: getattr(collision, key) for key in
                               ("collider", "victim", "colliderType", "victimType", "colliderSpeed", "victimSpeed", "type", "lane", "pos")
                               if hasattr(collision, key)})
        diagnostic = {"sim_s": self.now_s, "collisions": collisions,
                      "colliding_vehicle_ids": list(c.simulation.getCollidingVehiclesIDList()),
                      "teleport_started_ids": list(c.simulation.getStartingTeleportIDList()),
                      "teleport_ended_ids": list(c.simulation.getEndingTeleportIDList()),
                      "departed_ids": departed, "arrived_ids": arrived}
        self.raw_diagnostics.append(diagnostic)
        self._emit("road_diagnostics.jsonl", diagnostic)
        for collision in collisions:
            self._event("road_collision", collision=collision)
        for vid in diagnostic["teleport_started_ids"]:
            self._event("road_teleport_started", vehicle_id=vid)
        on_road_queues = {}
        for vid in vehicles:
            if c.vehicle.getSpeed(vid) < .1 and not c.vehicle.isStoppedParking(vid):
                edge_id = c.vehicle.getRoadID(vid)
                on_road_queues[edge_id] = on_road_queues.get(edge_id, 0) + 1
        edge_states = []
        for eid in sorted(self.metadata["edges"]):
            edge_states.append({"edge_id": eid, "vehicle_count": c.edge.getLastStepVehicleNumber(eid),
                                "halting_count": c.edge.getLastStepHaltingNumber(eid),
                                "queued_on_road_count": on_road_queues.get(eid, 0),
                                "mean_speed_m_s": c.edge.getLastStepMeanSpeed(eid),
                                "occupancy_percent": c.edge.getLastStepOccupancy(eid)})
        queue = sum(on_road_queues.values())
        self.max_queue_count = max(self.max_queue_count, queue)
        self.queue_vehicle_seconds += queue * self.tick_s
        truck = {"id": self.truck_id, "present": self.truck_id in vehicles, "distance_m": self.distance_m}
        if truck["present"]:
            native_distance = c.vehicle.getDistance(self.truck_id)
            if native_distance >= 0:
                if self._native_odometer is not None:
                    if native_distance + EPS < self._native_odometer:
                        raise RuntimeError("Persistent truck odometer moved backwards")
                    self.distance_m += max(0, native_distance - self._native_odometer)
                self._native_odometer = native_distance
            parked = c.vehicle.isStoppedParking(self.truck_id)
            speed = c.vehicle.getSpeed(self.truck_id)
            if self.active_leg and not parked and speed < .1:
                self.truck_waiting_tick_s += self.tick_s
            truck.update(edge_id=c.vehicle.getRoadID(self.truck_id), lane_id=c.vehicle.getLaneID(self.truck_id),
                         lane_position_m=c.vehicle.getLanePosition(self.truck_id), xy=list(c.vehicle.getPosition(self.truck_id)),
                         speed_m_s=speed, parked=bool(parked), distance_m=self.distance_m,
                         native_odometer_m=native_distance,
                         stopping_place_id=(c.vehicle.getStops(self.truck_id)[0].stoppingPlaceID
                                            if parked and c.vehicle.getStops(self.truck_id) else None),
                         native_waiting_s=c.vehicle.getWaitingTime(self.truck_id),
                         native_time_loss_s=c.vehicle.getTimeLoss(self.truck_id))
        elif self._native_odometer is not None:
            # A native vehicle waiting to leave an off-road parking area is
            # still registered but omitted from vehicle.getIDList(). SUMO uses
            # invalid coordinate/speed sentinels in that state. Keep it waiting
            # without inventing a position or removing/reinserting the vehicle.
            if self.truck_id in arrived:
                raise RuntimeError("Persistent truck ended its native route before endpoint")
            route = c.vehicle.getRoute(self.truck_id)  # Unknown/removed IDs fail here.
            if not route:
                raise RuntimeError("Persistent truck lost its native route")
            if self.active_leg:
                self.truck_waiting_tick_s += self.tick_s
            truck.update(native_vehicle_known=True, parking_exit_pending=True,
                         edge_id=None, lane_id=None, lane_position_m=None, xy=None,
                         speed_m_s=None, parked=False,
                         native_odometer_m=c.vehicle.getDistance(self.truck_id), stopping_place_id=None,
                         native_waiting_s=c.vehicle.getWaitingTime(self.truck_id),
                         native_time_loss_s=c.vehicle.getTimeLoss(self.truck_id))
        self._last_observation = {"observed_at_s": self.now_s, "truck": truck, "edges": edge_states,
                                  "network_queued_on_road_count": queue,
                                  "internal_edge_queued_count": sum(n for e, n in on_road_queues.items() if e not in self.metadata["edges"]),
                                  "traffic_lights": [{"id": tid, "current_state": c.trafficlight.getRedYellowGreenState(tid)}
                                                     for tid in sorted(self.metadata["tls_ids"])]}
        self._emit("road_states.jsonl", self._last_observation)

    def snapshot(self, now_s=None):
        now_s = self.now_s if now_s is None else _finite(now_s, "snapshot.now_s")
        if now_s + EPS < self.now_s:
            raise ValueError("Cannot return a road observation from the future")
        observation = copy.deepcopy(self._last_observation) if self._last_observation is not None else {
            "observed_at_s": 0.0, "truck": {"id": self.truck_id, "present": False, "initial_insertion_pending": True,
                                            "distance_m": 0.0}, "edges": [], "traffic_lights": []}
        observation.update(state_lag_s=max(0.0, now_s - observation["observed_at_s"]),
                           current_anchor_id=self.current_anchor,
                           active_leg_id=(self.active_leg or self.pending_leg or {}).get("leg_id"))
        return observation

    def finalize(self, endpoint_s=None):
        if self.closed:
            return copy.deepcopy(self.final_metrics)
        endpoint_s = self.now_s if endpoint_s is None else _finite(endpoint_s, "road endpoint")
        if endpoint_s + EPS < self.now_s:
            raise ValueError("Final endpoint must not predate already observed road state")
        active_ids = list(self.connection.vehicle.getIDList()) if self.connection else []
        if self.connection:
            try:
                self.connection.close()
            except BaseException:
                close_error = traceback.format_exc()
                self.failure = (self.failure + "\n" if self.failure else "") + close_error
                (self.path / "close_error.txt").write_text(close_error, encoding="utf-8")
            finally:
                self.connection = None
        if self.console:
            self.console.close()
        self.closed = True
        for leg in self.legs:
            if leg["status"] != "arrived":
                leg["status"] = "unfinished"
                leg["censored_at_observed_sim_s"] = self.now_s
                leg["elapsed_requested_to_observed_s"] = max(0, self.now_s - leg["requested_sim_s"])
                leg["realized_distance_until_observed_m"] = max(0, self.distance_m - leg["distance_start_m"]) if leg["distance_start_m"] is not None else 0.0
        trip_rows = []
        if (self.path / "tripinfo.xml").exists():
            try:
                trip_rows = [dict(row.attrib) for row in ET.parse(self.path / "tripinfo.xml").getroot().findall("tripinfo")]
            except ET.ParseError:
                self.failure = self.failure or "SUMO tripinfo XML is incomplete"
        scheduled = [r for r in getattr(self, "background", []) if r["requested_departure_s"] < endpoint_s - EPS]
        scheduled_ids = {r["id"] for r in scheduled}
        uninserted = sorted(scheduled_ids - self.background_departed)
        unfinished = sorted(self.background_departed - self.background_arrived)
        error_lines = (self.path / "sumo_errors.log").read_text(encoding="utf-8", errors="replace").splitlines() if (self.path / "sumo_errors.log").exists() else []
        native_collision_rows = []
        if (self.path / "collisions.xml").exists():
            try:
                native_collision_rows = [dict(e.attrib) for e in ET.parse(self.path / "collisions.xml").getroot()]
            except ET.ParseError:
                self.failure = self.failure or "SUMO collision XML is incomplete"
        source_unchanged = all(Path(p).is_file() and _hash(p) == digest for p, digest in getattr(self, "reused_sources", {}).items())
        counts = diagnostic_counts(self.raw_diagnostics)
        background_trips = [r for r in trip_rows if r.get("id", "").startswith("BG_")]
        own_source_unchanged = getattr(self, "manifest", {}).get("source_sha256") == _hash(__file__)
        collision_warnings = [line for line in error_lines if "collision" in line.lower()]
        teleport_warnings = [line for line in error_lines if "teleport" in line.lower()]
        valid = not self.failure and source_unchanged and own_source_unchanged and not native_collision_rows and not collision_warnings and not teleport_warnings and not any(counts.values())
        self.final_metrics = {"model_version": MODEL_VERSION, "simulation_only": True,
                              "status": "failed" if self.failure else "completed", "failure": self.failure,
                              "valid": valid,
                              "validity_definition": "No execution/close failure, unchanged reused/backend sources, zero native collision events/involved-vehicle ticks/XML records/warnings, and zero teleport starts/ends/warnings. Unfinished demand remains explicit and does not itself invalidate the dynamics.",
                              "endpoint_sim_s": endpoint_s, "last_observed_sim_s": self.now_s,
                              "state_lag_s": endpoint_s - self.now_s,
                              "truck_distance_m": self.distance_m, "truck_waiting_tick_s": self.truck_waiting_tick_s,
                              "road_queue_vehicle_seconds": self.queue_vehicle_seconds,
                              "max_network_halting_vehicle_count": self.max_queue_count,
                              "completed_road_legs": sum(l["status"] == "arrived" for l in self.legs),
                              "unfinished_road_legs": sum(l["status"] != "arrived" for l in self.legs),
                              "background_requested_all": len(getattr(self, "background", [])),
                              "background_requested_before_endpoint": len(scheduled),
                              "background_departed_count": len(self.background_departed),
                              "background_arrived_count": len(self.background_arrived),
                              "background_uninserted_count": len(uninserted), "background_unfinished_count": len(unfinished),
                              "background_uninserted_ids": uninserted, "background_unfinished_ids": unfinished,
                              "native_active_vehicle_ids_at_last_tick": active_ids,
                              "native_tripinfo_record_count": len(trip_rows),
                              "native_collision_xml_count": len(native_collision_rows),
                              "background_native_waiting_time_sum_s": sum(float(r.get("waitingTime", 0)) for r in background_trips),
                              "background_native_time_loss_sum_s": sum(float(r.get("timeLoss", 0)) for r in background_trips),
                              "background_native_depart_delay_sum_s": sum(float(r.get("departDelay", 0)) for r in background_trips),
                              "native_collision_warning_lines": collision_warnings,
                              "native_teleport_warning_lines": teleport_warnings,
                              "reused_sources_unchanged": source_unchanged,
                              "backend_source_unchanged": own_source_unchanged, **counts,
                              "persistent_truck_tripinfo_interpretation": "Truck remains parked/active until endpoint by design. Its unfinished native tripinfo is not an unfinished delivery leg; inspect road_legs.json and order receipts separately.",
                              "censoring": "No step after last fixed road tick; fractional endpoint lag is explicit. Uninserted demand and active road legs are retained without fabricated arrivals."}
        _save(self.path / "road_legs.json", self.legs)
        _save(self.path / "native_tripinfo.json", trip_rows)
        _save(self.path / "native_collisions.json", native_collision_rows)
        _save(self.path / "road_metrics.json", self.final_metrics)
        hashes = {str(p.relative_to(self.path)): _hash(p) for p in self.path.rglob("*")
                  if p.is_file() and not p.name.endswith(".jsonl")}
        for stream in self._streams.values():
            stream.close()
        hashes.update({name: _hash(self.path / name) for name in self._streams})
        _save(self.path / "artifact_sha256.json", hashes)
        return copy.deepcopy(self.final_metrics)

    close = finalize
