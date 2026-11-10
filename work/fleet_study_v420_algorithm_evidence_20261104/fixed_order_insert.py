"""Exhaustive freight adaptation of the single-transfer insertion class of KaRRiT (§2).

The supplier already has the parcel. Insert a handoff and a delivery on the chosen
receiver while maintaining the relative order of every scheduled old service.
Evaluate all legal insertions under the same traffic predictor and customer objective.
"""
import math

def select_plans(c, w, vehicle, hub, initial, score, legal, limit):
    if limit < 1 or initial["receiver"] != vehicle or initial["hub"] != hub or not legal(initial):
        raise ValueError("Expected one legal incumbent on this receiver/hub branch")
    baseline = list(initial["route"][vehicle])
    if baseline.count("X") != 1 or baseline.count("i") != 1:
        raise ValueError("Incumbent must have one handoff and one delivery")
    old = [token for token in baseline if token not in {"X", "i"}]
    if not old or old[0] != baseline[0]:
        raise ValueError("The already committed first service must stay first")
    alternatives = [initial]
    rejects = 0
    for pickup_after in range(1, len(old) + 1):
        for delivery_after in range(pickup_after, len(old) + 1):
            route = old[:pickup_after] + ["X"] + old[pickup_after:delivery_after] + ["i"] + old[delivery_after:]
            if route == baseline:
                continue
            routes = dict(initial["route"], **{vehicle: route})
            candidate = dict(initial, route=routes)
            if legal(candidate):
                alternatives.append(candidate)
            else:
                rejects += 1
    if len(alternatives) > limit:
        raise ValueError(f"Exact insertion would require {len(alternatives)} calls under cap {limit}")
    values = [float(score(candidate)) for candidate in alternatives]
    if not all(map(math.isfinite, values)):
        raise ValueError("Nonfinite common traffic forecast")
    best = min(range(len(values)), key=values.__getitem__)
    return alternatives[best], dict(evaluations=len(values),budget=limit,stop="all_feasible_insertions",
                                    infeasible=rejects,initial_score=values[0],best_score=values[best])
