#!/usr/bin/env python3
"""
Robotic Arm Trajectory Anomaly Detection

Detects:
  1. Collision risk  - trajectory passes too close to defined obstacle boundaries
  2. Jitter anomaly  - high-frequency oscillation / vibration in the motion path
  3. Root cause analysis via LLM (Chinese) when anomalies detected

Input  : JSON via stdin  {"points": [{"x","y","z","timestamp"}, ...]}
Output : JSON via stdout {"has_collision_risk","has_jitter_anomaly",
         "collision_risk_score","jitter_score","anomalies":[...],
         "root_cause_analysis": "..."}
"""

import os
import sys
import json
import math
import urllib.request
import urllib.error
import ssl
from typing import List, Dict, Any, Optional


DEFAULT_COLLISION_THRESHOLD = 50.0
DEFAULT_JITTER_THRESHOLD = 2.5
DEFAULT_JITTER_WINDOW = 5
DEFAULT_VELOCITY_SPIKE_FACTOR = 3.0
DEFAULT_LLM_TIMEOUT = 15
DEFAULT_MAX_ANOMALIES_FOR_LLM = 50

OBSTACLE_BOUNDARIES = [
    {"x_min": -20, "x_max": 20, "y_min": -20, "y_max": 20, "z_min": -50, "z_max": -30},
    {"x_min": 200, "x_max": 250, "y_min": -30, "y_max": 30, "z_min": 0, "z_max": 50},
]

LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")


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


def build_trajectory_summary(points: List[Dict]) -> str:
    if not points:
        return "无轨迹数据"
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    zs = [p["z"] for p in points]
    total_dist = 0.0
    for i in range(1, len(points)):
        total_dist += euclidean_distance(points[i - 1], points[i])
    return (
        f"轨迹点数: {len(points)}, "
        f"X 范围: [{min(xs):.2f}, {max(xs):.2f}], "
        f"Y 范围: [{min(ys):.2f}, {max(ys):.2f}], "
        f"Z 范围: [{min(zs):.2f}, {max(zs):.2f}], "
        f"总路径长度: {total_dist:.2f}mm"
    )


def call_llm(prompt: str) -> Optional[str]:
    if not LLM_API_KEY:
        return None

    url = f"{LLM_API_BASE.rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一名资深机械臂故障诊断工程师，擅长通过轨迹运行日志分析异常原因。"
                        "你的回答必须简洁专业，使用中文，控制在 200 字以内。"
                        "请直接给出诊断结论和建议，不要使用 markdown 格式。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 400,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )

    try:
        ctx = ssl._create_unverified_context() if "https" in url else None
        with urllib.request.urlopen(req, timeout=DEFAULT_LLM_TIMEOUT, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
        print(f"[WARN] LLM call failed: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[WARN] Unexpected LLM error: {e}", file=sys.stderr)
        return None


def analyze_root_cause(
    points: List[Dict],
    collision_result: Dict,
    jitter_result: Dict,
) -> Optional[str]:
    all_anomalies = collision_result["anomalies"] + jitter_result["anomalies"]
    if not all_anomalies:
        return None

    truncated = all_anomalies[:DEFAULT_MAX_ANOMALIES_FOR_LLM]
    anomaly_summary_lines = []
    for a in truncated:
        sev = a.get("severity", 0)
        anomaly_summary_lines.append(
            f"- [{a['type']}] 第{a['pointIndex']}点 (严重度 {sev:.2f}): {a['description']}"
        )
    if len(all_anomalies) > len(truncated):
        anomaly_summary_lines.append(
            f"- ... 另有 {len(all_anomalies) - len(truncated)} 条异常未全部列出"
        )

    anomaly_types = set(a["type"] for a in all_anomalies)

    prompt = f"""
机械臂轨迹出现异常，请根据以下信息诊断可能的原因并给出建议。
请重点考虑：
- COLLISION_RISK：可能是程序坐标写错、路径规划错误、或者机械臂原点偏移
- JITTER_ANOMALY：可能是关节生锈、减速器磨损、电机老化、PID 参数不合适
- VELOCITY_SPIKE：可能是控制器程序 bug、编码器故障、或者规划路径跳变

【轨迹概览】
{build_trajectory_summary(points)}

【异常统计】
- 碰撞风险: {'是' if collision_result['has_collision_risk'] else '否'} (得分 {collision_result['collision_risk_score']})
- 抖动异常: {'是' if jitter_result['has_jitter_anomaly'] else '否'} (得分 {jitter_result['jitter_score']})
- 异常类型集合: {', '.join(sorted(anomaly_types))}
- 总异常条数: {len(all_anomalies)}

【异常明细】
{chr(10).join(anomaly_summary_lines)}

请直接给出诊断结论：1) 最可能的根因；2) 次要可能原因；3) 维修/调试建议。简洁作答。
""".strip()

    return call_llm(prompt)


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
                    "root_cause_analysis": None,
                },
                ensure_ascii=False,
            )
        )
        return

    collision_result = detect_collision_risk(points)
    jitter_result = detect_jitter_anomaly(points)

    root_cause = None
    if collision_result["has_collision_risk"] or jitter_result["has_jitter_anomaly"]:
        root_cause = analyze_root_cause(points, collision_result, jitter_result)

    combined = {
        "has_collision_risk": collision_result["has_collision_risk"],
        "has_jitter_anomaly": jitter_result["has_jitter_anomaly"],
        "collision_risk_score": collision_result["collision_risk_score"],
        "jitter_score": jitter_result["jitter_score"],
        "anomalies": collision_result["anomalies"] + jitter_result["anomalies"],
        "root_cause_analysis": root_cause,
    }

    print(json.dumps(combined, ensure_ascii=False))


if __name__ == "__main__":
    main()
