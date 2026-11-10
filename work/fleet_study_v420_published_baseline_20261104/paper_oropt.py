"""Budgeted freight adaptation of the oriented traffic Or-opt in Gmira et al., §4."""
from math import isfinite


def route_key(plan):
    return tuple((actor, tuple(stops)) for actor, stops in sorted(plan["route"].items()))


def select_plans(c, w, vehicle, hub, initial, score, legal, limit):
    """Return best evaluated feasible plan and diagnostics for one vehicle/site branch."""
    if limit < 1:
        raise ValueError("A budget must include the incumbent evaluation.")
    if initial["receiver"] != vehicle or initial["hub"] != hub or not legal(initial):
        raise ValueError("Invalid common starting plan for this branch.")
    actors = [vehicle] + sorted(actor for actor in initial["route"] if actor != vehicle)
    initial_value = float(score(initial))
    if not isfinite(initial_value):
        raise ValueError("The common starting plan must have a finite objective.")
    values = {route_key(initial): initial_value}
    best_plan, best_value = initial, initial_value
    changes = []
    attempts = rejects = cache_hits = 0

    def finish(reason):
        return best_plan, dict(evaluations=len(values), budget=limit, stop=reason,
                               attempts=attempts, infeasible=rejects, cache_hits=cache_hits,
                               initial_score=initial_value, best_score=best_value,
                               accepted_moves=changes)

    incumbent, base = initial, initial_value
    while True:
        accepted = False
        for size in (3, 2, 1):
            for actor in actors:
                seq = list(incumbent["route"][actor])
                # Index zero is the already committed customer and cannot move.
                for start in range(1, len(seq) - size + 1):
                    block = seq[start:start + size]
                    rest = seq[:start] + seq[start + size:]
                    block_best, block_value = incumbent, base
                    for dest in range(1, len(rest) + 1):
                        if dest == start:
                            continue
                        attempts += 1
                        moved = rest[:dest] + block + rest[dest:]
                        routes = dict(incumbent["route"])
                        routes[actor] = moved
                        candidate = dict(incumbent, route=routes)
                        if not legal(candidate):
                            rejects += 1
                            continue
                        key = route_key(candidate)
                        if key in values:
                            value = values[key]
                            cache_hits += 1
                        else:
                            if len(values) >= limit:
                                return finish("forecast_cap")
                            value = float(score(candidate))
                            if not isfinite(value):
                                raise ValueError("A legal candidate has a nonfinite objective.")
                            values[key] = value
                        if value < best_value:
                            best_plan, best_value = candidate, value
                        if value < block_value:
                            block_best, block_value = candidate, value
                    if block_value < base:
                        changes.append({"actor": actor, "size": size, "start": start,
                                        "from_score": base, "to_score": block_value})
                        incumbent, base = block_best, block_value
                        accepted = True
                        break
                if accepted:
                    break
            if accepted:
                break
        if not accepted:
            return finish("local_optimum")
