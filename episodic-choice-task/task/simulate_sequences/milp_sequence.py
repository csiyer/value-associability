#!/usr/bin/env python3
"""
Two-phase MILP solver for episodic-choice-task trial sequences.

Phase 1 (~3k binary vars): assign old/new + delays to all 312 positions.
  Enforces that the total count of each delay d across all old trials = 3 × DELAY_COUNTS[d],
  so Phase 2 can distribute them equally across bins.

Phase 2 (~624 binary vars): assign a memorability-bin permutation to each triplet,
  so that each bin receives exactly the right delay distribution.

Outputs a JSON file with the trial sequence.
"""

import itertools
import json
import sys
import time
from collections import Counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csc_matrix, lil_matrix

# ── Parameters ────────────────────────────────────────────────────────────────
N = 312
MIN_DELAY = 9
MAX_DELAY = 12
DELAYS = list(range(MIN_DELAY, MAX_DELAY + 1))   # [9..12], 4 values
N_DELAYS = len(DELAYS)
N_TRIPLETS = N // 3   # 104
N_BINS = 3
BIN_NAMES = ["high", "mid", "low"]
N_OLD_PER_BIN = N_TRIPLETS // 2   # 52

# Per-bin delay histogram: 52 / 4 = 13 exactly — no rounding needed
DELAY_COUNTS = {d: 13 for d in DELAYS}
assert sum(DELAY_COUNTS.values()) == N_OLD_PER_BIN

# Total old trials with each delay across all 3 bins
TOTAL_PER_DELAY = {d: N_BINS * DELAY_COUNTS[d] for d in DELAYS}   # {7:15, 8:15, 9:18, …}

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1: assign old/new + delay to each of the 312 positions
# ══════════════════════════════════════════════════════════════════════════════
#
# Variables (all binary):
#   old[i]         i = 0..311        — trial i is old
#   delay[i,d_i]   valid (i,d) pairs — trial i has delay DELAYS[d_i]

delay_map = {}   # (i, d_idx) -> variable index
_idx = N         # old[i] occupies indices 0..N-1
for i in range(MIN_DELAY, N):
    for d_idx, d in enumerate(DELAYS):
        j = i - d
        if 0 <= j < N:
            delay_map[(i, d_idx)] = _idx
            _idx += 1
N_DELAY_VARS = _idx - N
N_VARS_P1 = _idx
print(f"Phase 1  variables : {N_VARS_P1}  (old={N}, delay={N_DELAY_VARS})")

# ── Constraint helpers ────────────────────────────────────────────────────────
def _build_milp(n_vars, row_dicts, lbs, ubs, time_limit=120, label=""):
    A = lil_matrix((len(row_dicts), n_vars))
    for r, rd in enumerate(row_dicts):
        for col, val in rd.items():
            A[r, col] = val
    t0 = time.time()
    print(f"{label} solving ({len(row_dicts)} constraints)…")
    res = milp(
        np.zeros(n_vars),
        constraints=LinearConstraint(csc_matrix(A), np.array(lbs), np.array(ubs)),
        integrality=np.ones(n_vars),
        bounds=Bounds(0, 1),
        options={"time_limit": time_limit, "disp": True},
    )
    print(f"{label} finished in {time.time()-t0:.1f}s | status={res.status} | {res.message}")
    return res

rows1, lbs1, ubs1 = [], [], []

def p1_eq(rd, v):  rows1.append(rd); lbs1.append(float(v));   ubs1.append(float(v))
def p1_leq(rd, u): rows1.append(rd); lbs1.append(-np.inf);    ubs1.append(float(u))

# A. Total old trials = 156
p1_eq({i: 1 for i in range(N)}, N_BINS * N_OLD_PER_BIN)

# B. No old trial in the first MIN_DELAY positions
for i in range(MIN_DELAY):
    p1_eq({i: 1}, 0)

# C. Each old trial has exactly one delay:  Σ_d delay[i,d] = old[i]
for i in range(N):
    rd = {i: -1}
    for d_idx in range(N_DELAYS):
        if (i, d_idx) in delay_map:
            rd[delay_map[(i, d_idx)]] = 1
    p1_eq(rd, 0)

# D. Source trial must be new:  delay[i,d] + old[i-d] ≤ 1
for (i, d_idx), var in delay_map.items():
    j = i - DELAYS[d_idx]
    p1_leq({var: 1, j: 1}, 1)

# E. Each new trial used as source at most once:
#    Σ_{(i,d): i-d=j} delay[i,d]  +  old[j]  ≤  1
for j in range(N):
    rd = {j: 1}
    for d_idx, d in enumerate(DELAYS):
        i = j + d
        if (i, d_idx) in delay_map:
            rd[delay_map[(i, d_idx)]] = rd.get(delay_map[(i, d_idx)], 0) + 1
    p1_leq(rd, 1)

# F. Total old trials with each delay = 3 × DELAY_COUNTS[d]  (enables equal split in Phase 2)
for d_idx, d in enumerate(DELAYS):
    rd = {delay_map[(i, d_idx)]: 1 for i in range(N) if (i, d_idx) in delay_map}
    p1_eq(rd, TOTAL_PER_DELAY[d])

res1 = _build_milp(N_VARS_P1, rows1, lbs1, ubs1, time_limit=120, label="Phase 1")
if res1.x is None:
    print("Phase 1: no solution found.")
    sys.exit(1)

x1 = np.round(res1.x).astype(int)
old_flag = x1[:N]                                   # 1 = old, 0 = new
delay_of = {i: DELAYS[d_idx]                        # position -> delay (old only)
            for (i, d_idx), var in delay_map.items()
            if x1[var] == 1}

print(f"\nPhase 1 decoded: {sum(old_flag)} old trials")
print(f"  Delay histogram: {sorted(Counter(delay_of.values()).items())}")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2: assign bin permutations to triplets
# ══════════════════════════════════════════════════════════════════════════════
#
# Each triplet t can take one of 6 permutations of {high, mid, low} across its
# 3 positions.  We choose permutations to achieve identical delay distributions
# across bins.
#
# Variables (all binary):  perm[t, k]   — triplet t uses permutation k

PERMS = list(itertools.permutations(range(N_BINS)))   # 6 permutations
N_PERM_VARS = N_TRIPLETS * len(PERMS)   # 104 × 6 = 624

def perm_var(t, k): return t * len(PERMS) + k

rows2, lbs2, ubs2 = [], [], []
def p2_eq(rd, v):  rows2.append(rd); lbs2.append(float(v));  ubs2.append(float(v))

# A. Each triplet uses exactly one permutation
for t in range(N_TRIPLETS):
    p2_eq({perm_var(t, k): 1 for k in range(len(PERMS))}, 1)

# B. Each bin receives exactly N_OLD_PER_BIN old trials
for b in range(N_BINS):
    rd = {}
    for t in range(N_TRIPLETS):
        for k, perm in enumerate(PERMS):
            # perm[p] = bin index assigned to position p within the triplet
            for p in range(3):
                if perm[p] == b:
                    i = t * 3 + p
                    if old_flag[i] == 1:
                        pv = perm_var(t, k)
                        rd[pv] = rd.get(pv, 0) + 1
    p2_eq(rd, N_OLD_PER_BIN)

# C. For each bin b and delay d: exactly DELAY_COUNTS[d] old trials in bin b have delay d
for b in range(N_BINS):
    for d in DELAYS:
        target = DELAY_COUNTS[d]
        rd = {}
        for t in range(N_TRIPLETS):
            for k, perm in enumerate(PERMS):
                for p in range(3):
                    if perm[p] == b:
                        i = t * 3 + p
                        if old_flag[i] == 1 and delay_of.get(i) == d:
                            pv = perm_var(t, k)
                            rd[pv] = rd.get(pv, 0) + 1
        p2_eq(rd, target)

print(f"\nPhase 2  variables : {N_PERM_VARS}")
res2 = _build_milp(N_PERM_VARS, rows2, lbs2, ubs2, time_limit=60, label="Phase 2")
if res2.x is None:
    print("Phase 2: no solution found.")
    sys.exit(1)

x2 = np.round(res2.x).astype(int)

# Decode bin assignment
bin_of = {}   # position index -> bin name
for t in range(N_TRIPLETS):
    for k, perm in enumerate(PERMS):
        if x2[perm_var(t, k)] == 1:
            for p in range(3):
                bin_of[t * 3 + p] = BIN_NAMES[perm[p]]
            break

# ── Assemble final trial list ─────────────────────────────────────────────────
trials = []
for i in range(N):
    is_old = bool(old_flag[i])
    d = delay_of.get(i)
    trials.append({
        "trial_number": i + 1,
        "memorability_bin": bin_of[i],
        "trial_type": "old" if is_old else "new",
        "source_trial_number": (i - d + 1) if is_old else None,   # 1-indexed
        "delay": d,
    })

# ── Validate ──────────────────────────────────────────────────────────────────
print("\nValidating…")
errors = []
old_trials = [t for t in trials if t["trial_type"] == "old"]
new_trials  = [t for t in trials if t["trial_type"] == "new"]

if len(old_trials) != 156: errors.append(f"old count={len(old_trials)}, expected 156")
if len(new_trials) != 156: errors.append(f"new count={len(new_trials)}, expected 156")

for b in BIN_NAMES:
    n = sum(1 for t in old_trials if t["memorability_bin"] == b)
    if n != N_OLD_PER_BIN: errors.append(f"bin {b}: {n} old, expected {N_OLD_PER_BIN}")

for t in old_trials:
    if not (MIN_DELAY <= t["delay"] <= MAX_DELAY):
        errors.append(f"trial {t['trial_number']}: delay {t['delay']} out of range")
    src = trials[t["source_trial_number"] - 1]
    if src["trial_type"] != "new":
        errors.append(f"trial {t['trial_number']}: source {t['source_trial_number']} is not new")

src_counts = Counter(t["source_trial_number"] for t in old_trials)
for src_num, cnt in src_counts.items():
    if cnt > 1: errors.append(f"source trial {src_num} used {cnt} times")

for t in trials[:MIN_DELAY]:
    if t["trial_type"] == "old": errors.append(f"trial {t['trial_number']} is old within first {MIN_DELAY}")

for t_idx in range(N_TRIPLETS):
    bins = [trials[t_idx*3+p]["memorability_bin"] for p in range(3)]
    if sorted(bins) != sorted(BIN_NAMES):
        errors.append(f"triplet {t_idx}: bins {bins}")

for b in BIN_NAMES:
    bin_delays = [t["delay"] for t in old_trials if t["memorability_bin"] == b]
    counts = Counter(bin_delays)
    for d in DELAYS:
        if counts[d] != DELAY_COUNTS[d]:
            errors.append(f"bin {b}, delay {d}: got {counts[d]}, expected {DELAY_COUNTS[d]}")

if errors:
    print("VALIDATION FAILED:")
    for e in errors: print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("All checks passed.")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\nDelay distribution (should be identical across bins):")
for b in BIN_NAMES:
    bin_delays = [t["delay"] for t in old_trials if t["memorability_bin"] == b]
    counts = Counter(bin_delays)
    print("  " + b + ": " + "  ".join(f"d{d}={counts[d]}" for d in DELAYS))

# ── Save ──────────────────────────────────────────────────────────────────────
out = {
    "metadata": {
        "n_trials": N,
        "min_delay": MIN_DELAY,
        "max_delay": MAX_DELAY,
        "delay_counts_per_bin": DELAY_COUNTS,
    },
    "trials": trials,
}
out_path = "sequence_solution.json"
with open(out_path, "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to {out_path}")
