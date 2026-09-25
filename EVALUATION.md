# Evaluation record: `tenant-config-race`

All checks and trials below were run locally by the author against the task as committed at
**`7bb7184`** (`tasks/tenant-config-race`), unless a row says otherwise. Job directories named here
live under `jobs/` (git-ignored; available on request).

> **Outcome: the task does NOT meet the standard-trial requirement.** Both required frontier
> configurations produced a passing solution on their first attempt (Codex: valid trial, reward 1;
> Claude Code: the attempt hit a subscription session limit, so it is excluded as invalid, but the
> code it left behind also passed the verifier). Static checks, oracle, nop and Docker build pass.
> See [`TRIAL_ANALYSIS.md`](TRIAL_ANALYSIS.md) for how the models solved it and what that implies.

## Environment

| Item | Value |
|---|---|
| Task commit | `7bb7184717047ccabd73fedce9badbb50646000a` |
| Upstream TB3 reference | `harbor-framework/terminal-bench` @ `4def1f3` (checks, rubric, hack prompt, CI defaults) |
| Harbor | `0.23.1.dev202609170426` (same as upstream `.github/harbor-version`) |
| Execution | local Docker 28.5.1 on macOS arm64 (`--env docker`) |
| Auth | Codex: ChatGPT subscription (`CODEX_FORCE_AUTH_JSON=1`); Claude Code: subscription OAuth token (`CLAUDE_FORCE_OAUTH=1`, token passed via environment, not argv) |

## Agent/model configuration

The assessment specifies **codex `gpt-6-sol` xhigh** and **claude-code Opus 5.5 max**. Upstream's
`.github/harbor-run-defaults.yml` at `4def1f3` lists `openai/gpt-6-astra` (xhigh) and
`anthropic/claude-fable-5-1` (max, `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`), changed on 2026-09-21 in
upstream PR #2047. The required trials use the configurations named by the assessment; the Claude
model ID is `anthropic/claude-opus-5-5` (the assessment's `claude-opus-5.5` is not a valid ID).
`CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` is also exported, as in upstream CI. Earlier results on the
CI-default models are listed separately below.

## Commands

```bash
# Static checks: every script listed in upstream .github/workflows/static-checks.yml
bash scripts/checks/<check>.sh tasks/tenant-config-race        # run from an upstream checkout

# Oracle / nop (also exercises the Docker build)
harbor run -p tasks/tenant-config-race -a oracle -k 3
harbor run -p tasks/tenant-config-race -a nop

# Standard trials (/run)
harbor run -p tasks/tenant-config-race --agent codex --model openai/gpt-6-sol \
  --env docker --yes --ae CODEX_FORCE_AUTH_JSON=1 --ak reasoning_effort=xhigh
CLAUDE_CODE_OAUTH_TOKEN=... CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 \
harbor run -p tasks/tenant-config-race --agent claude-code --model anthropic/claude-opus-5-5 \
  --env docker --yes --ae CLAUDE_FORCE_OAUTH=1 --ak reasoning_effort=max

# (The flags passed with --ae above were exported as environment variables instead for later runs;
#  see the tooling note below.)

# Adversarial trials (/cheat): same, plus upstream docs/prompts/hack-trial-prompt.md
#   --extra-instruction-path <upstream>/docs/prompts/hack-trial-prompt.md

# Implementation rubric: upstream scripts/review/stage_task.py + review_agent/review_model
python3 scripts/review/stage_task.py --repository <owner>/<repo> --commit <sha> \
  --task-path tasks/tenant-config-race <stage-dir>
harbor run --path <stage-dir> --agent claude-code --model anthropic/claude-sonnet-5 \
  --allow-agent-host api.anthropic.com
```

## Automated checks

| Check | Result | Evidence |
|---|---|---|
| Static checks (25 scripts) | **25/25 pass** | upstream `scripts/checks` @ `4def1f3` |
| Docker build | **pass** | built for every oracle/nop run below |
| Oracle | **1.0 (3/3)** | `jobs/freeze-oracle-x3` |
| Nop | **0.0** | `jobs/freeze-nop` |
| Implementation rubric (official staging/evaluator) | **34 pass / 1 N/A / 0 fail** | `jobs/official-rubric-7bb7184` (staged from commit `7bb7184` with upstream `stage_task.py`; reviewer claude-code / claude-sonnet-5; N/A: `artifact_efficiency`) |

## Standard trials (/run) — required configurations, commit `7bb7184`

Validity rule (fixed before running): an attempt counts only if the agent finished without an
agent crash, API/auth/rate-limit error, container failure or timeout, and the verifier ran.
Invalid attempts are listed under *Excluded attempts*. The invalid Claude attempt was not rerun (see the notes in the table).

| # | Agent / model | Reasoning | Valid | Reward | Verifier | Job |
|---|---|---|---|---|---|---|
| 1 | codex / openai/gpt-6-sol | xhigh | **yes** | **1.0 (solved)** | 2/2 tests passed; 8/8 lag rounds read in the lag window | `jobs/final-codex-sol-t1` |
| 2 | codex / openai/gpt-6-sol | xhigh | not run | — | — | stopped: requirement already failed by trial 1 |
| 3 | codex / openai/gpt-6-sol | xhigh | not run | — | — | stopped: requirement already failed by trial 1 |
| 1 | claude-code / anthropic/claude-opus-5-5 | max | **no** (HTTP 429 session limit) | (verifier: pass) | 2/2 tests passed on the code left behind; 4/8 lag rounds in window | `jobs/final-claude-opus55-t1` |
| 2 | claude-code / anthropic/claude-opus-5-5 | max | not run | — | — | one attempt consumed a full 5-hour subscription window |
| 3 | claude-code / anthropic/claude-opus-5-5 | max | not run | — | — | as above |

Both agents started at 05:47 UTC on 2026-09-24. The Codex agent finished at 06:01 UTC (~14.5 min);
the Claude agent ran until 07:14 UTC (65 turns) and ended with `ApiRateLimitError` ("You've hit your session
limit"); Harbor still collected `/app` and ran the verifier, which passed.

**Tooling note.** Passing `CODEX_FORCE_AUTH_JSON=1` / `CLAUDE_FORCE_OAUTH=1` with `--ae`, as in the
assessment's sample commands, makes Harbor treat the value `1` as a secret and replace every
literal `1` in the job output with `[REDACTED]`, including `verifier/reward.txt`, `result.json`
(which becomes invalid JSON) and timestamps. Rewards above were therefore read from the pytest
output (`verifier/test-stdout.txt`), which is unambiguous (`2 passed`). Later runs export these
variables in the environment instead, which Harbor reads identically without redaction.

## Adversarial trials (/cheat) — commit `7bb7184`

| Agent / model | Reward | Notes | Job |
|---|---|---|---|
| codex / openai/gpt-6-sol xhigh | **0** | Agent stopped after ~1.5 min by OpenAI's safety filter on the red-team prompt ("flagged for possible cybersecurity risk"; Harbor `AgentSafetyRefusalError`). Its only recorded plan was to widen the writer role's privileges during restart and read from the primary, which cannot work in the verifier (fresh provisioning, app runs as `nobody` with only the given roles). The verifier ran on the unchanged app: 2/2 tests failed. | `jobs/final-codex-sol-cheat` |
| claude-code / anthropic/claude-opus-5-5 max | **not run** | Skipped to meet the submission deadline: the only Opus 5.5 max run consumed a full 5-hour subscription window, so this trial could not be expected to finish (or finish validly) in time. | — |

The cheat trials use upstream `docs/prompts/hack-trial-prompt.md` (at `4def1f3`) via
`--extra-instruction-path`, which is how upstream's `/cheat` appends it. Reward 0 for the Codex
trial is reported as observed, but because the agent was refused by the provider's safety filter
rather than failing to find an exploit, it is weak evidence of verifier robustness. Robustness
evidence comes mainly from the verifier design (see *Verification explanation* in
`tasks/tenant-config-race/README.md`) and from read-only security reviews by a separate model during
development, whose findings were fixed before the final commit.

## Excluded attempts

- `jobs/final-claude-opus55-t1`: claude-code / claude-opus-5-5, `ApiRateLimitError` (HTTP 429,
  subscription session limit) after 65 turns. Excluded as an API/rate-limit failure. Its final
  `/app` nonetheless passed the verifier, so it is evidence that the task is solvable by this
  configuration, not evidence of a model failure.

Earlier Claude attempts on previous versions were excluded for billing
("Credit balance is too low"), a corrupted OAuth token (HTTP 400) and subscription usage limits (HTTP 429).

## Earlier results on upstream CI-default models and earlier task versions

| Task version | Agent / model | Result | Job |
|---|---|---|---|
| `5ece0df` (single PostgreSQL, hints present) | codex / gpt-6-astra xhigh | 3/3 solved | `jobs/codex-standard` |
| `2dd1574` (hints removed, verifier hardened) | codex / gpt-6-astra xhigh | 1/1 solved | `jobs/codex-frozen-standard-1` |
| `7bb7184` (primary/replica redesign) | codex / gpt-6-astra xhigh | 1/1 solved | `jobs/codex-optc-standard-1` |
| `7bb7184` | claude-code / claude-fable-5-1 max | not run (subscription usage for this model exhausted) | — |

These solves drove the redesign history summarized in the task README's change log.
