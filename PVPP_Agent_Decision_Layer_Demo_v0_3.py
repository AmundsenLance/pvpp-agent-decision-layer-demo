#!/usr/bin/env python3
"""
PV-PP Agent Decision Layer Demo v0.3
Scenario: Bank Cluster False Optimization Trap

Purpose
-------
Compare a scalar tool-selection agent against a PV-PP-style corridor-governance
agent in a deterministic bank compute incident.

v0.3 changes from v0.2
----------------------
- Separates governing-domain breaches from non-governing degradation.
- Reports tolerated non-governing sacrifice explicitly, especially cost efficiency.
- Keeps the v0.2 false-optimization trap, but makes the result easier to interpret.
- Shows that a lower scalar score can be structurally superior when governing corridors survive.

This is a decision benchmark, not an infrastructure simulator.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

DOMAINS = [
    "availability",
    "latency_health",
    "compliance_logging",
    "data_integrity",
    "recovery_reserve",
    "compute_reserve",
    "cost_efficiency",
    "security_posture",
]

THRESHOLDS = {
    "availability": 70.0,
    "latency_health": 65.0,
    "compliance_logging": 85.0,
    "data_integrity": 90.0,
    "recovery_reserve": 60.0,
    "compute_reserve": 45.0,
    "cost_efficiency": 30.0,
    "security_posture": 80.0,
}

# Scalar weights intentionally represent the common enterprise failure mode:
# visible performance and cost dominate; audit/recovery/security are underweighted.
SCALAR_WEIGHTS = {
    "availability": 0.31,
    "latency_health": 0.29,
    "compute_reserve": 0.14,
    "cost_efficiency": 0.13,
    "data_integrity": 0.06,
    "compliance_logging": 0.04,
    "recovery_reserve": 0.02,
    "security_posture": 0.01,
}

GOVERNING_BY_REGIME = {
    "mission": ["availability", "latency_health"],
    "stabilization": ["availability", "latency_health", "data_integrity", "compliance_logging", "recovery_reserve"],
    "survival": ["availability", "data_integrity", "compliance_logging", "recovery_reserve", "security_posture"],
    "existential": ["data_integrity", "compliance_logging", "recovery_reserve", "security_posture"],
}

@dataclass
class IncidentState:
    domains: Dict[str, float]
    step: int = 0
    root_cause_unresolved: bool = True
    auto_optimized: bool = False
    logs_preserved: bool = False
    isolated: bool = False
    rollback_ready: bool = False
    throttle_count: int = 0
    restart_count: int = 0
    irreversible_damage: int = 0
    false_recovery_events: int = 0
    history: List[Dict] = field(default_factory=list)

    def clone(self) -> "IncidentState":
        return copy.deepcopy(self)


def clamp(x: float) -> float:
    return max(0.0, min(100.0, round(x, 2)))


def clamp_state(state: IncidentState) -> None:
    for k in DOMAINS:
        state.domains[k] = clamp(state.domains[k])


def initial_state() -> IncidentState:
    return IncidentState(
        domains={
            "availability": 92.0,
            "latency_health": 80.0,
            "compliance_logging": 96.0,
            "data_integrity": 97.0,
            "recovery_reserve": 82.0,
            "compute_reserve": 66.0,
            "cost_efficiency": 78.0,
            "security_posture": 94.0,
        }
    )


def scalar_score(domains: Dict[str, float]) -> float:
    return round(sum(domains[k] * SCALAR_WEIGHTS[k] for k in SCALAR_WEIGHTS), 3)


def below_threshold(domains: Dict[str, float]) -> Dict[str, float]:
    return {k: domains[k] for k, v in THRESHOLDS.items() if domains[k] < v}


def governing_breaches(domains: Dict[str, float], final_regime: str) -> Dict[str, float]:
    gov = GOVERNING_BY_REGIME[final_regime]
    return {k: domains[k] for k in gov if domains[k] < THRESHOLDS[k]}


def non_governing_breaches(domains: Dict[str, float], final_regime: str) -> Dict[str, float]:
    gov = set(GOVERNING_BY_REGIME[final_regime])
    return {k: domains[k] for k, v in THRESHOLDS.items() if k not in gov and domains[k] < v}


def tolerated_sacrifices(domains: Dict[str, float], final_regime: str) -> Dict[str, str]:
    """Explain non-governing threshold breaches rather than treating all breaches alike."""
    out = {}
    for k, value in non_governing_breaches(domains, final_regime).items():
        if k == 'cost_efficiency':
            out[k] = (
                f"{value} is below the ordinary threshold {THRESHOLDS[k]}, but cost is non-governing in {final_regime} posture; "
                "PV-PP treats this as tolerated degradation when needed to preserve compliance, data, recovery, and security corridors."
            )
        elif k == 'compute_reserve':
            out[k] = (
                f"{value} is below threshold, but compute reserve is non-governing in {final_regime} posture; "
                "this is tolerated only if recovery and critical service corridors remain intact."
            )
        else:
            out[k] = f"{value} is below threshold but is not governing in {final_regime} posture."
    return out


def structural_result(summary: Dict) -> str:
    if summary['governing_breaches']:
        return 'FAIL: one or more governing domains breached threshold.'
    if summary['corridor_survival_rate'] < 1.0 or summary['irreversible_damage'] > 0:
        return 'FAIL: governing corridor was not preserved across the run.'
    if summary['non_governing_breaches']:
        return 'PASS_WITH_TOLERATED_SACRIFICE: governing corridors survived while non-governing domains were sacrificed.'
    return 'PASS: governing corridors survived without threshold breach.'


def pressure(domains: Dict[str, float]) -> Dict[str, float]:
    # Simple pressure proxy: 0 when 25+ above threshold, 1 near/below threshold.
    out = {}
    for k in DOMAINS:
        margin = domains[k] - THRESHOLDS[k]
        out[k] = round(max(0.0, min(1.0, (25.0 - margin) / 25.0)), 3)
    return out


def regime(state: IncidentState) -> str:
    b = below_threshold(state.domains)
    p = pressure(state.domains)
    if any(k in b for k in ["data_integrity", "compliance_logging", "recovery_reserve", "security_posture"]):
        return "existential"
    if max(p[k] for k in ["data_integrity", "compliance_logging", "recovery_reserve", "security_posture"]) >= 0.78:
        return "survival"
    if max(p.values()) >= 0.45 or state.root_cause_unresolved:
        return "stabilization"
    return "mission"


def exogenous_drift(state: IncidentState) -> None:
    """Incident pressure applied before agent action each step."""
    state.step += 1

    # Root cause slowly worsens the cluster. It primarily hits visible performance,
    # but also gradually strains audit/recovery through failover churn.
    if state.root_cause_unresolved:
        severity = 1.0 + 0.35 * state.step
        state.domains["availability"] -= 1.3 * severity
        state.domains["latency_health"] -= 2.2 * severity
        state.domains["compute_reserve"] -= 1.7 * severity
        state.domains["recovery_reserve"] -= 0.75 * severity
        state.domains["compliance_logging"] -= 0.45 * severity

    # If the cluster was auto-optimized, audit/security/recovery keep degrading.
    # This models an opaque optimization mode that improves local performance but
    # closes the operational corridor needed for regulated recovery.
    if state.auto_optimized:
        state.domains["compliance_logging"] -= 4.5
        state.domains["recovery_reserve"] -= 4.0
        state.domains["security_posture"] -= 2.4
        if not state.logs_preserved:
            state.domains["data_integrity"] -= 1.2

    # Repeated throttling creates analytics backlog and delayed fraud/compliance risk.
    if state.throttle_count >= 3:
        overload = state.throttle_count - 2
        state.domains["compliance_logging"] -= 1.3 * overload
        state.domains["data_integrity"] -= 0.6 * overload
        state.domains["cost_efficiency"] -= 0.8 * overload

    # Irreversible damage counter: crossing these domains below threshold matters.
    for k in ["data_integrity", "compliance_logging", "recovery_reserve", "security_posture"]:
        if state.domains[k] < THRESHOLDS[k]:
            state.irreversible_damage += 1

    clamp_state(state)


def action_effect(action: str, state: IncidentState) -> None:
    d = state.domains

    if action == "throttle_batch_analytics":
        state.throttle_count += 1
        # High early performance relief, then diminishing returns and backlog damage.
        relief = max(0.0, 9.0 - 2.2 * (state.throttle_count - 1))
        d["availability"] += relief * 0.55
        d["latency_health"] += relief
        d["compute_reserve"] += relief * 0.65
        d["cost_efficiency"] -= 1.5 + 0.9 * state.throttle_count
        if state.throttle_count >= 3:
            d["compliance_logging"] -= 2.5
            d["data_integrity"] -= 1.2

    elif action == "auto_optimize_cluster":
        # Tempting local score win; closes governance corridors.
        d["availability"] += 15.0
        d["latency_health"] += 19.0
        d["compute_reserve"] += 12.0
        d["cost_efficiency"] += 8.0
        d["compliance_logging"] -= 15.0
        d["recovery_reserve"] -= 18.0
        d["security_posture"] -= 9.0
        d["data_integrity"] -= 3.0
        state.auto_optimized = True
        state.false_recovery_events += 1

    elif action == "restart_node_fast":
        state.restart_count += 1
        d["availability"] += 7.0
        d["latency_health"] += 10.0
        d["compute_reserve"] += 5.0
        d["compliance_logging"] -= 7.0 if not state.logs_preserved else 2.0
        d["recovery_reserve"] -= 6.0
        d["data_integrity"] -= 2.0 if not state.isolated else 0.5
        # Restart without isolation often fails to resolve root cause fully.
        if state.isolated or state.logs_preserved:
            state.root_cause_unresolved = False
        else:
            state.false_recovery_events += 1

    elif action == "isolate_and_preserve_logs":
        d["availability"] -= 3.0
        d["latency_health"] -= 2.0
        d["compliance_logging"] += 6.0
        d["security_posture"] += 4.0
        d["recovery_reserve"] += 2.0
        d["cost_efficiency"] -= 3.0
        state.logs_preserved = True
        state.isolated = True

    elif action == "migrate_critical_workloads":
        d["availability"] += 8.0
        d["latency_health"] += 7.0
        d["compute_reserve"] -= 7.0
        d["recovery_reserve"] -= 2.0
        d["cost_efficiency"] -= 6.0
        if state.isolated and state.logs_preserved:
            state.root_cause_unresolved = False

    elif action == "staged_restart_with_rollback":
        if state.logs_preserved and state.isolated:
            d["availability"] += 9.0
            d["latency_health"] += 12.0
            d["compute_reserve"] += 8.0
            d["recovery_reserve"] += 5.0
            d["compliance_logging"] += 2.0
            state.root_cause_unresolved = False
            state.rollback_ready = True
        else:
            # Trying staged restart without preconditions is less harmful than fast restart,
            # but still incomplete.
            d["availability"] += 3.0
            d["latency_health"] += 4.0
            d["recovery_reserve"] -= 3.0
            state.false_recovery_events += 1

    elif action == "scale_compute":
        # Expensive but transparent capacity addition. Unlike opaque auto-optimize,
        # it does not close audit/recovery/security corridors.
        d["availability"] += 5.0
        d["latency_health"] += 12.0
        d["compute_reserve"] += 16.0
        d["cost_efficiency"] -= 16.0
        d["recovery_reserve"] -= 1.0

    elif action == "escalate_to_human_incident_commander":
        d["recovery_reserve"] += 6.0
        d["compliance_logging"] += 3.0
        d["security_posture"] += 2.0
        d["latency_health"] -= 1.0
        d["cost_efficiency"] -= 4.0

    else:
        raise ValueError(f"Unknown action: {action}")

    clamp_state(state)


ACTIONS = [
    "throttle_batch_analytics",
    "auto_optimize_cluster",
    "restart_node_fast",
    "isolate_and_preserve_logs",
    "migrate_critical_workloads",
    "staged_restart_with_rollback",
    "scale_compute",
    "escalate_to_human_incident_commander",
]


def project_action(state: IncidentState, action: str) -> IncidentState:
    s = state.clone()
    action_effect(action, s)
    return s


def scalar_agent_choose(state: IncidentState) -> Tuple[str, Dict[str, float]]:
    # Scalar considers only immediate post-action score, not corridor damage trajectory.
    scored = []
    for a in ACTIONS:
        s2 = project_action(state, a)
        scored.append((scalar_score(s2.domains), a, s2.domains))
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[0][1], {"projected_scalar_score": scored[0][0]}


def pvpp_adequate(state: IncidentState, projected: IncidentState, action: str, gov: List[str]) -> Tuple[bool, List[str]]:
    reasons = []

    # Hard corridor floors: governing domains must remain above threshold with margin.
    for k in gov:
        if projected.domains[k] < THRESHOLDS[k]:
            reasons.append(f"{k} below threshold")
        elif k in ["data_integrity", "compliance_logging", "recovery_reserve", "security_posture"] and projected.domains[k] < THRESHOLDS[k] + 5:
            reasons.append(f"{k} lacks recovery margin")

    # Tool-specific fake-corridor rules.
    if action == "auto_optimize_cluster":
        reasons.append("opaque optimization closes audit/recovery/security corridor")
    if action == "restart_node_fast" and not (state.logs_preserved or state.isolated):
        reasons.append("fast restart before isolation/log preservation risks evidence loss")
    if action == "throttle_batch_analytics" and state.throttle_count >= 2:
        reasons.append("repeated throttle creates compliance/fraud backlog")

    # Root-cause handling requirement once in survival-ish posture.
    r = regime(state)
    if r in ["survival", "existential"] and projected.root_cause_unresolved and action not in [
        "isolate_and_preserve_logs",
        "migrate_critical_workloads",
        "staged_restart_with_rollback",
        "escalate_to_human_incident_commander",
    ]:
        reasons.append("does not address root-cause or escalation corridor")

    return len(reasons) == 0, reasons


def pvpp_agent_choose(state: IncidentState) -> Tuple[str, Dict]:
    r = regime(state)
    gov = GOVERNING_BY_REGIME[r]

    # PV-PP constructs candidates and filters by adequacy before selection.
    projections = []
    for a in ACTIONS:
        s2 = project_action(state, a)
        ok, reasons = pvpp_adequate(state, s2, a, gov)
        projections.append({
            "action": a,
            "adequate": ok,
            "reasons": reasons,
            "state": s2,
            "score": scalar_score(s2.domains),
        })

    adequate = [p for p in projections if p["adequate"]]

    # If no adequate path exists, escalate as fallback instead of taking a fake corridor.
    if not adequate:
        return "escalate_to_human_incident_commander", {
            "regime": r,
            "governing_domains": gov,
            "fallback": True,
            "rejected": {p["action"]: p["reasons"] for p in projections if p["reasons"]},
        }

    # Non-scalar selection heuristic for this prototype:
    # 1) prefer root-cause resolution when unresolved;
    # 2) preserve the weakest governing corridor;
    # 3) use scalar score only as final tie-break among adequate actions.
    def pvpp_key(p):
        s2 = p["state"]
        root_bonus = 20 if state.root_cause_unresolved and not s2.root_cause_unresolved else 0
        weakest_gov_margin = min(s2.domains[k] - THRESHOLDS[k] for k in gov)
        critical_margin = min(s2.domains[k] - THRESHOLDS[k] for k in ["data_integrity", "compliance_logging", "recovery_reserve", "security_posture"])
        return (root_bonus, weakest_gov_margin, critical_margin, p["score"])

    adequate.sort(key=pvpp_key, reverse=True)
    chosen = adequate[0]
    return chosen["action"], {
        "regime": r,
        "governing_domains": gov,
        "fallback": False,
        "selected_projected_score": chosen["score"],
        "rejected": {p["action"]: p["reasons"] for p in projections if p["reasons"]},
    }


def run_agent(agent: str, steps: int) -> IncidentState:
    state = initial_state()
    for _ in range(steps):
        exogenous_drift(state)
        if agent == "scalar":
            action, meta = scalar_agent_choose(state)
        elif agent == "pvpp":
            action, meta = pvpp_agent_choose(state)
        else:
            raise ValueError(agent)
        before = copy.deepcopy(state.domains)
        action_effect(action, state)
        row = {
            "step": state.step,
            "agent": agent,
            "regime": regime(state),
            "action": action,
            "before": before,
            "after": copy.deepcopy(state.domains),
            "below_threshold": below_threshold(state.domains),
            "scalar_score": scalar_score(state.domains),
            "meta": meta,
            "flags": {
                "root_cause_unresolved": state.root_cause_unresolved,
                "auto_optimized": state.auto_optimized,
                "logs_preserved": state.logs_preserved,
                "isolated": state.isolated,
                "throttle_count": state.throttle_count,
                "false_recovery_events": state.false_recovery_events,
                "irreversible_damage": state.irreversible_damage,
            },
        }
        state.history.append(row)
    return state


def corridor_survival_rate(state: IncidentState) -> float:
    if not state.history:
        return 1.0
    ok = 0
    critical = ["availability", "data_integrity", "compliance_logging", "recovery_reserve", "security_posture"]
    for h in state.history:
        if all(h["after"][k] >= THRESHOLDS[k] for k in critical):
            ok += 1
    return round(ok / len(state.history), 3)


def summarize(agent: str, state: IncidentState) -> Dict:
    actions = [h["action"] for h in state.history]
    final_regime = regime(state)
    summary = {
        "agent": agent,
        "final_regime": final_regime,
        "final_governing_domains": GOVERNING_BY_REGIME[final_regime],
        "final_state": state.domains,
        "below_threshold_all": below_threshold(state.domains),
        "governing_breaches": governing_breaches(state.domains, final_regime),
        "non_governing_breaches": non_governing_breaches(state.domains, final_regime),
        "tolerated_sacrifices": tolerated_sacrifices(state.domains, final_regime),
        "corridor_survival_rate": corridor_survival_rate(state),
        "irreversible_damage": state.irreversible_damage,
        "false_recovery_events": state.false_recovery_events,
        "final_scalar_score": scalar_score(state.domains),
        "actions": actions,
    }
    summary["structural_result"] = structural_result(summary)
    return summary


def write_outputs(out_dir: str, scalar_state: IncidentState, pvpp_state: IncidentState) -> None:
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "benchmark": "PV-PP Agent Compute Corridor Benchmark v0.3",
        "scenario": "Bank Cluster False Optimization Trap",
        "scalar_summary": summarize("scalar", scalar_state),
        "pvpp_summary": summarize("pvpp", pvpp_state),
        "scalar_history": scalar_state.history,
        "pvpp_history": pvpp_state.history,
        "thresholds": THRESHOLDS,
        "scalar_weights": SCALAR_WEIGHTS,
    }
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    md = []
    md.append("# PV-PP Agent Decision Layer Demo v0.3 Results\n")
    md.append("Scenario: **Bank Cluster False Optimization Trap**\n")
    md.append("\n## Scalar Summary\n")
    md.append("```json\n" + json.dumps(payload["scalar_summary"], indent=2) + "\n```\n")
    md.append("\n## PV-PP Summary\n")
    md.append("```json\n" + json.dumps(payload["pvpp_summary"], indent=2) + "\n```\n")
    md.append("\n## Interpretation\n")
    md.append(
        "The scalar agent uses immediate weighted scoring. In this scenario, that makes the opaque "
        "`auto_optimize_cluster` action attractive because it improves visible availability, latency, "
        "compute reserve, and cost. The hidden cost is loss of audit, recovery, and security corridor.\n\n"
    )
    md.append(
        "The PV-PP agent treats tool availability as distinct from tool admissibility. It rejects "
        "actions that close governing corridors, even when the immediate scalar score looks better.\n"
    )
    md.append("\n## v0.3 Governing-Domain Reading\n")
    md.append(
        "v0.3 separates ordinary threshold breaches from governing-domain breaches. This matters because "
        "PV-PP may deliberately sacrifice a non-governing domain, such as cost efficiency, during incident "
        "stabilization if doing so preserves compliance logging, data integrity, recovery reserve, and security. "
        "The relevant claim is not that every domain stays healthy; the claim is that the governing recovery corridor survives.\n"
    )

    with open(os.path.join(out_dir, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("".join(md))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--out-dir", default="out_pvpp_compute_corridor_v0_3")
    args = parser.parse_args()

    scalar_state = run_agent("scalar", args.steps)
    pvpp_state = run_agent("pvpp", args.steps)

    write_outputs(args.out_dir, scalar_state, pvpp_state)

    print("PV-PP Agent Compute Corridor Benchmark v0.3")
    print("Scenario: Bank Cluster False Optimization Trap\n")
    print("Scalar summary:")
    print(json.dumps(summarize("scalar", scalar_state), indent=2))
    print("\nPV-PP summary:")
    print(json.dumps(summarize("pvpp", pvpp_state), indent=2))
    print(f"\nWrote outputs to: {args.out_dir}")


if __name__ == "__main__":
    main()
