"""Streaming pipeline defense using only documented toolkit calls."""
from api import Verdict


def register(ctx):
    for event, handler in (("data_batch", check_data_batch), ("contract_checkpoint", check_contract_checkpoint), ("lineage_run", check_lineage_run), ("feature_materialization", check_feature_materialization), ("embedding_batch", check_embedding_batch)):
        ctx.on(event, handler)


def decide(ctx, pillar, reasons, payload, observation):
    return Verdict(alert=bool(reasons), pillar=pillar, reason="; ".join(reasons) if reasons else "Within calibrated limits")


def median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def subtle_signals(ctx, group, metrics):
    """Score current observations against past values before updating history.

    Bounds remain the hard guardrail. Two-sided 3-sigma bounds provide a
    calibrated variance prior. Upper-only metrics need 12 past observations
    to estimate their center. MAD resists isolated bad observations; the
    published bound provides a variance floor against overconfident fitting.
    No labels, event IDs or phase information are used.
    """
    histories = ctx.state.setdefault("metric_history", {}).setdefault(group, {})
    reasons = []
    for name, value, lower, upper in metrics:
        past = histories.setdefault(name, [])
        if lower is not None:
            center = (lower + upper) / 2
            scale = (upper - lower) / 6
            deviation = abs(value - center)
        elif len(past) >= 12:
            center = median(past)
            mad = median([abs(x - center) for x in past])
            scale = max(1.4826 * mad, (upper - center) / 3, abs(upper) * 0.02)
            deviation = value - center
        else:
            center, scale, deviation = 0, 1, 0
        if scale > 0 and deviation > 2.5 * scale:
            reasons.append(name + " moderate statistical anomaly")
        # Exclude only violations of published bounds from calibration.
        # Candidate alerts do not censor their own future reference sample.
        if value <= upper and (lower is None or value >= lower):
            past.append(value)
            if len(past) > 128:
                del past[0]
    return reasons


def check_data_batch(payload, ctx):
    p = ctx.tools.batch_profile(payload["batch_id"])
    reasons = []
    if "error" in p:
        return Verdict(False, pillar="checks", reason=p["error"])
    b = ctx.baseline
    for field, low, high in (("row_count", b["row_count_min"], b["row_count_max"]), ("mean_amount", b["mean_amount_min"], b["mean_amount_max"]), ("staleness_min", 0, b["staleness_min_max"])):
        if not low <= p[field] <= high:
            reasons.append(field)
    if p["null_rate"]["customer_id"] > b["null_rate_max"]:
        reasons.append("customer_id null rate")
    reasons += subtle_signals(ctx, ("checks", payload.get("table", "")), [
        ("row_count", p["row_count"], b["row_count_min"], b["row_count_max"]),
        ("mean_amount", p["mean_amount"], b["mean_amount_min"], b["mean_amount_max"]),
        ("null_rate", p["null_rate"]["customer_id"], None, b["null_rate_max"]),
        ("staleness", p["staleness_min"], None, b["staleness_min_max"]),
    ])
    return decide(ctx, "checks", reasons, payload, p)


def check_contract_checkpoint(payload, ctx):
    p = ctx.tools.contract_diff(payload["contract_id"], payload["checkpoint_batch_id"])
    if "error" in p:
        return Verdict(False, pillar="contracts", reason=p["error"])
    reasons = list(p["violations"])
    if p["freshness_delay_min"] > ctx.baseline["freshness_delay_max_min"]:
        reasons.append("freshness SLA")
    reasons += subtle_signals(ctx, ("contracts", payload["contract_id"]), [
        ("freshness", p["freshness_delay_min"], None, ctx.baseline["freshness_delay_max_min"]),
    ])
    return decide(ctx, "contracts", reasons, payload, p)


def check_lineage_run(payload, ctx):
    p = ctx.tools.lineage_graph_slice(payload["run_id"])
    if "error" in p:
        return Verdict(False, pillar="lineage", reason=p["error"])
    reasons = []
    if p["duration_ms"] > ctx.baseline["lineage_duration_ms_max"]:
        reasons.append("runtime")
    upstream = tuple(sorted(p["actual_upstream"]))
    declared = {item["name"] for item in payload.get("inputs", [])}
    if not declared.issubset(set(upstream)):
        reasons.append("missing declared upstream")
    if p["actual_downstream_count"] < len(payload.get("outputs", [])):
        reasons.append("orphaned output")
    # Learn the modal topology per job from past events, without labels.
    history = ctx.state.setdefault("lineage_topologies", {}).setdefault(payload.get("job", ""), {})
    if history:
        expected = max(history, key=history.get)
        if history[expected] >= 3 and upstream != expected:
            reasons.append("upstream topology changed")
    history[upstream] = history.get(upstream, 0) + 1
    reasons += subtle_signals(ctx, ("lineage", payload.get("job", "")), [
        ("runtime", p["duration_ms"], None, ctx.baseline["lineage_duration_ms_max"]),
    ])
    return decide(ctx, "lineage", reasons, payload, p)


def check_feature_materialization(payload, ctx):
    p = ctx.tools.feature_drift(payload["feature_view"], payload["batch_id"])
    if "error" in p:
        return Verdict(False, pillar="ai_infra", reason=p["error"])
    reasons = ["training-serving skew"] if p["mean_shift_sigma"] > ctx.baseline["feature_mean_shift_sigma_max"] else []
    reasons += subtle_signals(ctx, ("feature", payload["feature_view"]), [
        ("skew", p["mean_shift_sigma"], None, ctx.baseline["feature_mean_shift_sigma_max"]),
    ])
    return decide(ctx, "ai_infra", reasons, payload, p)


def check_embedding_batch(payload, ctx):
    p = ctx.tools.embedding_drift(payload["corpus"], payload["chunk_batch_id"])
    if "error" in p:
        return Verdict(False, pillar="ai_infra", reason=p["error"])
    reasons = []
    if p["centroid_shift"] > ctx.baseline["embedding_centroid_shift_max"]:
        reasons.append("embedding drift")
    if p["avg_doc_age_days"] > ctx.baseline["corpus_avg_doc_age_days_max"]:
        reasons.append("stale corpus")
    reasons += subtle_signals(ctx, ("embedding", payload["corpus"]), [
        ("centroid", p["centroid_shift"], None, ctx.baseline["embedding_centroid_shift_max"]),
        ("document_age", p["avg_doc_age_days"], None, ctx.baseline["corpus_avg_doc_age_days_max"]),
    ])
    return decide(ctx, "ai_infra", reasons, payload, p)
