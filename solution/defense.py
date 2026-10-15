"""Streaming pipeline defense using only documented toolkit calls."""
from api import Verdict


def register(ctx):
    for event, handler in (("data_batch", check_data_batch), ("contract_checkpoint", check_contract_checkpoint), ("lineage_run", check_lineage_run), ("feature_materialization", check_feature_materialization), ("embedding_batch", check_embedding_batch)):
        ctx.on(event, handler)


def decide(ctx, pillar, reasons, payload, observation):
    return Verdict(alert=bool(reasons), pillar=pillar, reason="; ".join(reasons) if reasons else "Within calibrated limits")


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
    return decide(ctx, "checks", reasons, payload, p)


def check_contract_checkpoint(payload, ctx):
    p = ctx.tools.contract_diff(payload["contract_id"], payload["checkpoint_batch_id"])
    if "error" in p:
        return Verdict(False, pillar="contracts", reason=p["error"])
    reasons = list(p["violations"])
    if p["freshness_delay_min"] > ctx.baseline["freshness_delay_max_min"]:
        reasons.append("freshness SLA")
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
    return decide(ctx, "lineage", reasons, payload, p)


def check_feature_materialization(payload, ctx):
    p = ctx.tools.feature_drift(payload["feature_view"], payload["batch_id"])
    if "error" in p:
        return Verdict(False, pillar="ai_infra", reason=p["error"])
    reasons = ["training-serving skew"] if p["mean_shift_sigma"] > ctx.baseline["feature_mean_shift_sigma_max"] else []
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
    return decide(ctx, "ai_infra", reasons, payload, p)
