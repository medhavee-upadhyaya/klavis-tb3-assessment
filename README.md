# Terminal-Bench 3 task submission: `tenant-config-race`

An original Terminal-Bench 3 task, built and evaluated with the upstream TB3 tooling
(`harbor-framework/terminal-bench` @ `4def1f3`, Harbor `0.23.1.dev202609170426`).

| Where | What |
|---|---|
| [`tasks/tenant-config-race/`](tasks/tenant-config-race/) | The task: `instruction.md`, `task.toml`, environment, reference solution, verifier, and a README with the design, difficulty, solution and verification explanations and the full change log |
| [`EVALUATION.md`](EVALUATION.md) | Commands, configurations and results for every required check and trial, including excluded attempts |
| [`TRIAL_ANALYSIS.md`](TRIAL_ANALYSIS.md) | How the frontier models solved the task, why it did not resist them, and what I would change |

## Summary

The task asks an agent to make a multi-worker FastAPI config service correct in front of a
PostgreSQL primary, an asynchronous streaming read replica, and a Redis cache: coherent responses,
absolute read-after-acknowledged-write monotonicity under replica lag and Redis outages, Redis
fallback when replica read access is lost, and tenant isolation.

| Requirement | Result |
|---|---|
| Static checks | 25/25 pass |
| Implementation rubric | 34 pass, 1 N/A, 0 fail |
| Docker build, oracle, nop | pass; oracle 1.0 (3/3), nop 0.0 |
| Standard trials: all 3 per configuration must fail | **Not met.** codex / gpt-6-sol solved trial 1; claude-code / opus-5-5's trial 1 was cut off by a subscription limit, but the code it left passed the verifier |
| Adversarial trials: reward 0 | codex / gpt-6-sol: 0 (stopped by the provider's safety filter); claude-code / opus-5-5: **not run** (subscription quota) |

**The task does not meet TB3's difficulty requirement.** I am submitting it with the complete
evidence rather than overstating it; `TRIAL_ANALYSIS.md` explains why, and what a harder version
would look like.
