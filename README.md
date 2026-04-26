# pvpp-agent-decision-layer-demo
PV-PP Agent Decision Layer demo repository showing how the Productive Value, Productive Power framework can govern AI agents, tool use, thresholds, recovery corridors, and enterprise decision control beyond simple scalar scoring.
# pvpp-agent-decision-layer-demo

## Bank Cluster False Optimization Trap — v0.3

This repository demonstrates a small deterministic benchmark for comparing a scalar-scoring AI operations agent against a PV-PP-style agent decision layer in a bank infrastructure incident.

The benchmark is not a Kubernetes simulator. It is a decision benchmark. Its purpose is to show how different agent-governance architectures behave when an AI agent must choose among tool-like actions under threshold, compliance, recovery, and cascading-risk conditions.

## Core claim

A scalar agent can report a high score while destroying the system's recovery corridor.

A PV-PP agent can accept worse short-term scalar performance while preserving the governing domains needed for recovery.

In the v0.3 sample run, the scalar agent ends with a final scalar score of `90.616` but breaches compliance logging, data integrity, recovery reserve, and security posture. The PV-PP agent ends with a lower scalar score of `70.414`, but preserves all governing corridors and records zero irreversible damage.

## Scenario

A bank compute cluster is under incident pressure. The agent can choose actions resembling enterprise tool calls:

- auto-optimize cluster
- restart node fast
- throttle batch analytics
- isolate and preserve logs
- scale compute
- escalate to a human incident commander

The trap is that `auto_optimize_cluster` improves visible availability and latency while degrading compliance logging, recovery reserve, and security posture. A scalar optimizer repeatedly selects this attractive local action because it raises the weighted score. PV-PP rejects that path because it destroys the corridor needed to preserve the bank's governing domains.

## Domains tracked

The benchmark tracks eight domains:

- availability
- latency health
- compliance logging
- data integrity
- recovery reserve
- compute reserve
- cost efficiency
- security posture

Not every domain is governing in every regime. Under stabilization or crisis posture, PV-PP may tolerate degradation in non-governing domains such as cost efficiency in order to preserve compliance, data integrity, recovery reserve, and security posture.

## Sample result

### Scalar agent

```json
{
  "final_regime": "existential",
  "final_scalar_score": 90.616,
  "corridor_survival_rate": 0.0,
  "irreversible_damage": 34,
  "false_recovery_events": 9,
  "structural_result": "FAIL: one or more governing domains breached threshold."
}
```

The scalar agent looks successful by its own score, but structurally fails.

It preserves:

- availability
- latency health
- compute reserve
- cost efficiency

It destroys or severely damages:

- compliance logging
- data integrity
- recovery reserve
- security posture

### PV-PP agent

```json
{
  "final_regime": "stabilization",
  "final_scalar_score": 70.414,
  "corridor_survival_rate": 1.0,
  "irreversible_damage": 0,
  "false_recovery_events": 0,
  "structural_result": "PASS_WITH_TOLERATED_SACRIFICE: governing corridors survived while non-governing domains were sacrificed."
}
```

The PV-PP agent scores lower because it sacrifices cost efficiency, but it preserves the governing corridor. That is the point of the benchmark.

## Why scalar scoring fails here

Scalar scoring compresses all domains into one weighted number. That can be useful in stable, well-behaved environments. It becomes fragile when:

- some domains have hard thresholds;
- some failures are irreversible or semi-irreversible;
- short-term improvements hide downstream damage;
- auditability and recovery capacity cannot be casually traded away;
- tool actions have delayed cross-domain effects;
- the agent needs to preserve a recovery corridor, not merely maximize a visible score.

In this benchmark, the scalar agent repeatedly selects the locally attractive optimization tool. The score remains high even as the system loses compliance logging, recovery reserve, and security posture.

## What PV-PP does differently

PV-PP treats the problem as a structured decision process rather than a single-score optimization problem.

The simplified benchmark approximates the following PV-PP architecture:

```text
PPP → Φ → H → G → ℛ → Graph Layer / seed substrate → Π
→ Π completeness validation → Constraints → Domain Framing
→ Adequacy → Σ → ε
```

In practical agent terms:

- PPP: what the agent believes the system state is
- Φ: which domains are under pressure
- H: how close domains are to failure
- G: which domains are governing
- ℛ: which decision regime applies
- Graph / Π: which tool/action paths are reachable and constructed
- Constraints: which actions are permitted or feasible
- Domain Framing: what must be preserved
- Adequacy: whether the action preserves a real recovery corridor
- Σ: final non-scalar selection
- ε: execution and monitored realization

This benchmark implements only a toy approximation of that full stack. It is intended to demonstrate the difference in decision posture.

## How to run

```bash
python3 PVPP_Agent_Compute_Corridor_Benchmark_v0_3.py --steps 10 --out-dir out_pvpp_compute_corridor_v0_3
```

The script writes summary output and a results file to the selected output directory.

## Interpretation

This benchmark should not be read as evidence that every scalar system fails or that every PV-PP implementation succeeds. The narrower point is cleaner:

When an AI agent controls enterprise tools under threshold-sensitive, recovery-sensitive, compliance-sensitive conditions, scalar scoring can reward actions that look efficient while closing the recovery corridor. PV-PP is designed to make those corridor failures explicit before selection.

## Commercial relevance

For enterprise AI-agent deployment, especially in banking or regulated infrastructure, the key issue is not merely whether an agent can call tools. MCP, APIs, skills, CLIs, and workflow engines provide access. They do not by themselves decide which tool call is structurally admissible.

PV-PP is positioned here as a decision-governance layer above tool access. It asks:

- What is the agent trying to preserve?
- Which domains are governing right now?
- Which actions are fake recoveries?
- Which tool calls close the recovery corridor?
- Which sacrifices are tolerable because they are non-governing?
- When should the agent escalate rather than optimize?

## Current status

This is v0.3, a deterministic prototype.

It is suitable for:

- demonstration;
- discussion with technical evaluators;
- initial repository publication;
- illustrating the difference between scalar optimization and corridor governance.

It is not yet:

- production software;
- an infrastructure emulator;
- a complete MCP agent implementation;
- a validated enterprise risk model.

## Next development steps

Likely next versions should add:

- randomized incident seeds;
- multiple scenario families;
- configurable scalar weights;
- configurable threshold maps;
- action cooldown and action-history reporting;
- CSV output for comparative runs;
- a simple charting script;
- an MCP/tool-calling interpretation layer;
- stress cases where PV-PP can also fail if perception or candidate construction is wrong.

## One-line summary

Scalar optimization can preserve the score while destroying the system. PV-PP corridor governance preserves the system even when the score looks worse.
