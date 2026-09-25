# Trial analysis: `tenant-config-race`

**Result: the task does not meet TB3's difficulty bar.** On the final version (`7bb7184`), both
required configurations produced code that passes the verifier on the first attempt. There are
therefore no model failures to analyze; this document explains how the models succeeded, why
the task did not resist them, and what I would change. Numbers and job paths are in
[`EVALUATION.md`](EVALUATION.md).

## What the task asks

A FastAPI config gateway (4 worker processes) reads per-tenant configs through a Redis cache from
PostgreSQL. In the final design PostgreSQL is a primary (writes only, through a provisioned
function; the app's writer role cannot `SELECT` config rows) plus an asynchronous streaming read
replica (the only place the app can read config rows). The starting code has non-atomic cache
writes and trusts cache hits and replica reads. The four required invariants are coherence,
absolute (no grace period) read-after-acknowledged-write monotonicity, Redis fallback when replica
read access is lost, and tenant isolation. The verifier pauses replica WAL replay, disables the
app's Redis access, revokes its replica login, and checks every response against acknowledgment
order and PostgreSQL's committed state.

## How each model solved it

**codex / gpt-6-sol, xhigh — valid trial, reward 1** (`jobs/final-codex-sol-t1`, ~14.5 min).
A WAL fence on every read: sample `pg_current_wal_lsn()` on the primary (allowed for the writer
role; it reads no table), wait until the replica's `pg_last_wal_replay_lsn()` reaches it, then read.
Cache entries are written atomically by a Lua script and tagged with the fence LSN they were
validated against; a hit is served only if its LSN is at or past the current fence. This is the same
causal-read idea as the reference solution, with a cheaper cache-hit path.

**claude-code / claude-opus-5-5, max — excluded (HTTP 429 session limit), code passed the verifier**
(`jobs/final-claude-opus55-t1`, 65 turns). A different valid design: a `POST` does not return 200
until its generation is visible either in Redis (atomic, generation-ordered "claim"/"put" Lua
scripts) or on the replica (it waits for replay); a `GET` hit reads Redis and the replica in
parallel and returns the newer, and a miss or Redis outage does a fenced read using
`pg_current_wal_flush_lsn()` and a shared replay watcher. It also added explicit 503s and
per-request time budgets. The session limit ended the agent run, but its final `/app` passed
every check, including all lag rounds.

Earlier, codex / gpt-6-astra (the upstream CI default) also solved this version (1/1), and every
earlier version of the task (4/4).

## Why the task did not resist frontier models

1. **The requirement names the problem.** The instruction precisely states the invariants,
   including "no grace period" and "including while the replica has not yet replayed that update".
   Once stated, each is a recognizable distributed-systems pattern (atomic versioned cache write;
   read-your-writes via a WAL-position fence). Both models identified the right primitive within
   minutes of reading the code.
2. **The key capability is well documented.** WAL positions (`pg_current_wal_lsn`,
   `pg_last_wal_replay_lsn`) are the standard PostgreSQL answer to replica read-your-writes, widely
   described in documentation and blog posts. Restricting the app to built-in functions did not
   hide them; both models found and justified them explicitly.
3. **Everything is locally testable.** The environment reproduces the primary/replica setup, so
   an agent can pause replay itself and confirm its fix (gpt-6-sol's final message reports testing
   "a paused replica, Redis interruption and recovery, replica loss, 409 conflicts"). The task
   rewards careful engineering, which these models do well, rather than insight they lack.
4. **The search space is small.** Three Python files of about 100 lines each; the whole fix fits in
   a model's working context at once.

## Iteration history (short)

| Version | Change | Codex result |
|---|---|---|
| `5ece0df` | single PostgreSQL + Redis, invariants stated | 3/3 solved (astra) |
| `2dd1574` | removed solution hints; hardened verifier (source-of-truth reads, Redis ACL lock, 409/POST-body checks, protected-file hashes) | 1/1 solved (astra) |
| `7bb7184` | redesign: primary + streaming replica, role split, replica-lag rounds | 1/1 solved (astra), 1/1 solved (sol); Opus code also passed |

Each round removed an easy path (hints, then "validate against the database"), and each time the
model found the next standard technique. Verifier hardening made the task correct and hard to
exploit, not hard to solve.

## What I would do differently

- **Check difficulty first, polish later.** Run one frontier trial on a rough prototype before
  investing in verifier hardening; I polished a task whose difficulty was never established.
- **Make the difficulty come from facts the agent must discover, not from a named property.**
  For example, a CDC consumer built on PostgreSQL logical decoding that silently drifts from the
  source (unchanged TOASTed columns omitted from UPDATE records, commit-order versus
  acknowledgment order, redelivery after a crash from the last confirmed position), specified only
  by "the index must equal the database after any workload, including consumer crashes".
- **Budget subscription quota for evaluation.** One Opus 5.5 max trial consumed a full 5-hour
  subscription window, so the required runs need to be planned around quota resets.
