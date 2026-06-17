#!/usr/bin/env python3
"""
Robotic Arm Trajectory Anomaly Detection

Detects:
  1. Collision risk  - trajectory passes too close to defined obstacle boundaries
  2. Jitter anomaly  - high-frequency oscillation / vibration in the motion path

Input  : JSON via stdin  {"points": [{"x","y","z","timestamp"}, ...]}
Output : JSON via stdout {"has_collision_risk","has_jitter_anomaly",
         "collision_risk_score","jitter_score","anomalies":[...]}
"""

import sys
import json
import math
from typing import List, Dict, Any


DEFAULT_COLLISION_THRESHOLD = 50.0
DEFAULT_JITTER_THRESHOLD = 2.5
DEFAULT_JITTER_WINDOW = 5
DEFAULT_VELOCITY_SPIKE_FACTOR = 3.0

OBSTACLE_BOUNDARIES = [
    {"x_min": -20, "x_max": 20, "y_min": -20, "y_max": 20, "z_min": -50, "z_max": -30},
    {"x_min": 200, "x_max": 250, "y_min": -30, "y_max": 30, "z_min": 0, "z_max": 50},
]


def euclidean_distance(p1: Dict, p2: Dict) -> float:
    return math.sqrt(
        (p1["x"] - p2["x"]) ** 2
        + (p1["y"] - p2["y"]) ** 2
        + (p1["z"] - p2["z"]) ** 2
    )


def point_to_box_distance(px: float, py: float, pz: float, box: Dict) -> float:
    dx = max(box["x_min"] - px, 0, px - box["x_max"])
    dy = max(box["y_min"] - py, 0, py - box["y_max"])
    dz = max(box["z_min"] - pz, 0, pz - box["z_max"])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def detect_collision_risk(
    points: List[Dict],
    threshold: float = DEFAULT_COLLISION_THRESHOLD,
) -> Dict[str, Any]:
    anomalies = []
    min_distance = float("inf")

    for i, pt in enumerate(points):
        for box in OBSTACLE_BOUNDARIES:
            dist = point_to_box_distance(pt["x"], pt["y"], pt["z"], box)
            if dist < min_distance:
                min_distance = dist
            if dist < threshold:
                anomalies.append(
                    {
                        "type": "COLLISION_RISK",
                        "pointIndex": i,
                        "description": f"Point at ({pt['x']:.2f},{pt['y']:.2f},{pt['z']:.2f}) "
                        f"is {dist:.2f}mm from obstacle boundary (threshold={threshold})",
                        "severity": round(max(0, 1.0 - dist / threshold), 4),
                    }
                )

    score = round(max(0, 1.0 - min_distance / threshold), 4) if min_distance < threshold else 0.0
    return {
        "has_collision_risk": len(anomalies) > 0,
        "collision_risk_score": score,
        "anomalies": anomalies,
    }


def detect_jitter_anomaly(
    points: List[Dict],
    threshold: float = DEFAULT_JITTER_THRESHOLD,
    window: int = DEFAULT_JITTER_WINDOW,
    velocity_spike_factor: float = DEFAULT_VELOCITY_SPIKE_FACTOR,
) -> Dict[str, Any]:
    anomalies = []

    if len(points) < 3:
        return {
            "has_jitter_anomaly": False,
            "jitter_score": 0.0,
            "anomalies": [],
        }

    velocities = []
    for i in range(1, len(points)):
        p1, p2 = points[i - 1], points[i]
        dist = euclidean_distance(p1, p2)
        t1 = p1.get("timestamp", 0)
        t2 = p2.get("timestamp", 0)
        dt = abs(t2 - t1) if isinstance(t1, (int, float)) else 1.0
        if dt == 0:
            dt = 1.0
        velocities.append(dist / dt)

    if len(velocities) < 2:
        return {
            "has_jitter_anomaly": False,
            "jitter_score": 0.0,
            "anomalies": [],
        }

    mean_vel = sum(velocities) / len(velocities)

    for i in range(window, len(velocities)):
        window_vels = velocities[i - window : i]
        local_mean = sum(window_vels) / len(window_vels)
        local_var = sum((v - local_mean) ** 2 for v in window_vels) / len(window_vels)
        local_std = math.sqrt(local_var)

        if local_mean > 0 and local_std / local_mean > threshold:
            anomalies.append(
                {
                    "type": "JITTER_ANOMALY",
                    "pointIndex": i,
                    "description": f"High jitter detected at point {i}: "
                    f"CV={local_std / local_mean:.3f} (threshold={threshold})",
                    "severity": round(min(1.0, (local_std / local_mean) / (threshold * 2)), 4),
                }
            )

    for i, vel in enumerate(velocities):
        if mean_vel > 0 and vel > mean_vel * velocity_spike_factor:
            anomalies.append(
                {
                    "type": "VELOCITY_SPIKE",
                    "pointIndex": i + 1,
                    "description": f"Velocity spike at point {i + 1}: "
                    f"v={vel:.2f} vs mean={mean_vel:.2f} "
                    f"(factor={velocity_spike_factor}x)",
                    "severity": round(
                        min(1.0, (vel / mean_vel - velocity_spike_factor) / velocity_spike_factor), 4
                    ),
                }
            )

    cv = 0.0
    if mean_vel > 0:
        global_std = math.sqrt(sum((v - mean_vel) ** 2 for v in velocities) / len(velocities))
        cv = global_std / mean_vel

    score = round(min(1.0, cv / (threshold * 2)), 4) if cv > threshold else 0.0
    return {
        "has_jitter_anomaly": len(anomalies) > 0,
        "jitter_score": score,
        "anomalies": anomalies,
    }


def main():
    raw = sys.stdin.read()
    data = json.loads(raw)
    points = data.get("points", [])

    if not points:
        print(
            json.dumps(
                {
                    "has_collision_risk": False,
                    "has_jitter_anomaly": False,
                    "collision_risk_score": 0.0,
                    "jitter_score": 0.0,
                    "anomalies": [],
                }
            )
        )
        return

    collision_result = detect_collision_risk(points)
    jitter_result = detect_jitter_anomaly(points)

    combined = {
        "has_collision_risk": collision_result["has_collision_risk"],
        "has_jitter_anomaly": jitter_result["has_jitter_anomaly"],
        "collision_risk_score": collision_result["collision_risk_score"],
        "jitter_score": jitter_result["jitter_score"],
        "anomalies": collision_result["anomalies"] + jitter_result["anomalies"],
    }

    print(json.dumps(combined))


if __name__ == "__main__":
    main()
