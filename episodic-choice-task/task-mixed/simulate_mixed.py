#!/usr/bin/env python3
"""
simulate_mixed.py
─────────────────
Simulation for the new mixed-memorability episodic choice task.

Design
------
  • 152 new/new encoding trials are laid out first.  Each pairs 1 high-mem +
    1 low-mem item and is assigned a shared value ($0 or $1, balanced).
  • Participant picks one item; only the CHOSEN item enters the old pool
    (tagged with its memorability bin and value).
  • After each encoding trial the scheduler checks: does the current position
    have ≥1 eligible old-H item AND ≥1 eligible old-L item in the delay
    window [min_delay, max_delay]?
      → YES: insert one old/old retrieval trial, choosing the (H, L) pair
             whose type {1,2,3,4} is currently least frequent.
      → NO:  continue to the next encoding trial.
  • "Inserting" advances the trial counter, so it can affect future windows.

4 retrieval types
-----------------
  1  H=$0, L=$1   (optimal: pick L)
  2  H=$1, L=$0   (optimal: pick H)
  3  both=$0       (optimal_old_choice = NA)
  4  both=$1       (optimal_old_choice = NA)

Questions answered
------------------
  Q1. How many old/old trials does this scheme yield on average (at p=0.5)?
  Q2. How balanced are the 4 types?
  Q3. How sensitive are these to a memorability bias (p_high ≠ 0.5)?

Usage
-----
  python simulate_mixed.py                 # default sweep + figures
  python simulate_mixed.py --n_sim 5000
  python simulate_mixed.py --min_delay 7 --max_delay 20
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ── Defaults ───────────────────────────────────────────────────────────────────
N_ENC     = 152
MIN_DELAY = 7
MAX_DELAY = 15
N_SIM     = 2000
SEED      = 42


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════════════════════

def _trial_type(h_val, l_val):
    """Map (H-item value, L-item value) → retrieval type 1–4."""
    if   h_val == 0 and l_val == 1: return 1
    elif h_val == 1 and l_val == 0: return 2
    elif h_val == 0 and l_val == 0: return 3
    else:                           return 4


def _pick_smart(avail_H, avail_L, type_counts):
    """
    Among all (H, L) pairs available in the delay window, choose the one
    whose retrieval type is currently least frequent.
    Ties broken by earliest source trial (oldest first) to reduce item expiry.
    """
    best_h = best_l = None
    best_count = float('inf')
    for h in sorted(avail_H, key=lambda x: x[0]):
        for l in sorted(avail_L, key=lambda x: x[0]):
            t = _trial_type(h[1], l[1])
            if type_counts[t - 1] < best_count:
                best_count = type_counts[t - 1]
                best_h, best_l = h, l
    return best_h, best_l


# ══════════════════════════════════════════════════════════════════════════════
# Core simulation
# ══════════════════════════════════════════════════════════════════════════════

def run_one_sim(p_high, min_delay, max_delay, rng):
    """
    Simulate one participant.

    Algorithm
    ---------
    Iterate through the 152 encoding slots.  After each encoding trial,
    check whether the NEXT trial position has an eligible (H, L) pair in
    [min_delay, max_delay].  If yes, insert one old/old trial and advance
    the trial counter by one extra step.

    Parameters
    ----------
    p_high    : P(participant chooses the H item on each encoding trial)
    min_delay : int
    max_delay : int
    rng       : numpy Generator

    Returns
    -------
    dict with n_old, type_counts, total_trials, per-type details,
    and per-trial delay_H / delay_L lists for bias analysis.
    """
    # Balanced $0 / $1 values for the 152 encoding trials
    values = np.array([0] * (N_ENC // 2) + [1] * (N_ENC - N_ENC // 2))
    rng.shuffle(values)

    pool_H = []   # list of (trial_number_1indexed, $value)
    pool_L = []

    type_counts = [0, 0, 0, 0]
    trial_num   = 1   # absolute position in the final sequence (enc + ret)

    delays_H = []   # delay_H for each inserted retrieval trial
    delays_L = []   # delay_L for each inserted retrieval trial

    for enc_idx in range(N_ENC):
        # ── Process this encoding trial ──────────────────────────────────────
        enc_trial_num = trial_num
        val = int(values[enc_idx])
        if rng.random() < p_high:
            pool_H.append((enc_trial_num, val))
        else:
            pool_L.append((enc_trial_num, val))
        trial_num += 1   # encoding trial now occupies enc_trial_num

        # ── Check if we can insert an old/old trial at current trial_num ────
        ret_num = trial_num
        lo = ret_num - max_delay
        hi = ret_num - min_delay

        avail_H = [(tn, v) for tn, v in pool_H if lo <= tn <= hi]
        avail_L = [(tn, v) for tn, v in pool_L if lo <= tn <= hi]

        if avail_H and avail_L:
            h, l = _pick_smart(avail_H, avail_L, type_counts)
            t    = _trial_type(h[1], l[1])
            type_counts[t - 1] += 1
            pool_H.remove(h)
            pool_L.remove(l)
            delays_H.append(ret_num - h[0])
            delays_L.append(ret_num - l[0])
            trial_num += 1   # old trial occupies ret_num

    delays_H = np.array(delays_H) if delays_H else np.array([np.nan])
    delays_L = np.array(delays_L) if delays_L else np.array([np.nan])
    diff     = delays_H - delays_L   # positive → H waited longer

    return dict(
        n_old          = sum(type_counts),
        type_counts    = type_counts,
        total_trials   = trial_num - 1,
        n_type1        = type_counts[0],
        n_type2        = type_counts[1],
        n_type3        = type_counts[2],
        n_type4        = type_counts[3],
        # delay stats (per-participant means)
        mean_delay_H   = float(np.nanmean(delays_H)),
        mean_delay_L   = float(np.nanmean(delays_L)),
        mean_delay_diff= float(np.nanmean(diff)),   # H − L; >0 means H has longer delay
        std_delay_diff = float(np.nanstd(diff)),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sweep
# ══════════════════════════════════════════════════════════════════════════════

def run_sweep(p_high_values, n_sim, min_delay, max_delay, seed):
    rng  = np.random.default_rng(seed)
    rows = []

    for p_high in p_high_values:
        sims = [run_one_sim(p_high, min_delay, max_delay, rng) for _ in range(n_sim)]

        n_old    = np.array([s['n_old']        for s in sims])
        n_total  = np.array([s['total_trials'] for s in sims])
        tc       = np.array([s['type_counts']  for s in sims])   # (n_sim, 4)

        dH   = np.array([s['mean_delay_H']    for s in sims])
        dL   = np.array([s['mean_delay_L']    for s in sims])
        diff = np.array([s['mean_delay_diff'] for s in sims])   # H − L per participant

        rows.append(dict(
            p_high          = p_high,
            n_old_mean      = n_old.mean(),
            n_old_std       = n_old.std(),
            n_old_min       = n_old.min(),
            n_old_max       = n_old.max(),
            total_mean      = n_total.mean(),
            old_pct_mean    = (n_old / n_total).mean() * 100,
            type1_mean      = tc[:, 0].mean(),
            type2_mean      = tc[:, 1].mean(),
            type3_mean      = tc[:, 2].mean(),
            type4_mean      = tc[:, 3].mean(),
            type_min_mean   = tc.min(axis=1).mean(),
            type_min_p10    = np.percentile(tc.min(axis=1), 10),
            # delay bias
            delay_H_mean    = dH.mean(),     # mean delay for H items across participants
            delay_L_mean    = dL.mean(),     # mean delay for L items
            delay_diff_mean = diff.mean(),   # H − L  (positive → H waits longer)
            delay_diff_std  = diff.std(),    # between-participant SD of H−L
            delay_diff_p5   = np.percentile(diff,  5),
            delay_diff_p95  = np.percentile(diff, 95),
        ))

    return pd.DataFrame(rows)


def run_window_sweep(window_configs, p_high, n_sim, seed):
    """Sweep over (min_delay, max_delay) at a fixed p_high."""
    rng  = np.random.default_rng(seed)
    rows = []
    for min_d, max_d in window_configs:
        sims  = [run_one_sim(p_high, min_d, max_d, rng) for _ in range(n_sim)]
        n_old = np.array([s['n_old'] for s in sims])
        tc    = np.array([s['type_counts'] for s in sims])
        rows.append(dict(
            min_delay     = min_d,
            max_delay     = max_d,
            window_width  = max_d - min_d + 1,
            n_old_mean    = round(n_old.mean(), 1),
            n_old_std     = round(n_old.std(),  1),
            n_old_min     = int(n_old.min()),
            type_min_mean = round(tc.min(axis=1).mean(), 1),
            type_min_p10  = int(np.percentile(tc.min(axis=1), 10)),
        ))
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# Plotting
# ══════════════════════════════════════════════════════════════════════════════

def plot_delay_bias(df, min_delay, max_delay, out_dir):
    """
    Two panels:
      Left  – mean delay for H and L items as a function of p_high
      Right – mean(delay_H − delay_L) with 5th/95th percentile band
    A positive difference means H items sit in the pool longer before being
    tested — a potential confound if memorability affects forgetting rate.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle(
        f"Delay bias: H vs L items on old/old trials  "
        f"|  delay [{min_delay}–{max_delay}]  |  {N_SIM:,} sims/point",
        fontsize=11)
    p = df['p_high'].values

    # Panel 1: raw delays
    ax = axes[0]
    ax.plot(p, df['delay_H_mean'], 'o-', color='C0', label='mean delay (H item)')
    ax.plot(p, df['delay_L_mean'], 's-', color='C1', label='mean delay (L item)')
    ax.axhline((min_delay + max_delay) / 2, color='gray', lw=0.8, ls='--',
               label=f'window midpoint ({(min_delay+max_delay)/2:.0f})')
    ax.set_xlabel('p(choose H in encoding)', fontsize=10)
    ax.set_ylabel('Mean delay (trials)', fontsize=10)
    ax.set_title('Mean delay by memorability bin', fontsize=10)
    ax.legend(fontsize=8)

    # Panel 2: difference H − L
    ax = axes[1]
    ax.fill_between(p, df['delay_diff_p5'], df['delay_diff_p95'],
                    alpha=0.15, color='C3', label='5th–95th pct (between participants)')
    ax.fill_between(p,
                    df['delay_diff_mean'] - df['delay_diff_std'],
                    df['delay_diff_mean'] + df['delay_diff_std'],
                    alpha=0.30, color='C3', label='mean ± 1 SD')
    ax.plot(p, df['delay_diff_mean'], 'o-', color='C3', label='mean(delay_H − delay_L)')
    ax.axhline(0, color='k', lw=1.0, ls='--', label='no bias')
    ax.set_xlabel('p(choose H in encoding)', fontsize=10)
    ax.set_ylabel('delay_H − delay_L (trials)', fontsize=10)
    ax.set_title('H − L delay difference\n(>0 → H waits longer → potential confound)', fontsize=10)
    ax.legend(fontsize=8)

    plt.tight_layout()
    out = Path(out_dir) / f'sim_delay_bias_{min_delay}-{max_delay}.png'
    fig.savefig(out, dpi=150); plt.show()
    print(f"Figure saved → {out}")


def plot_p_sweep(df, min_delay, max_delay, out_dir):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle(
        f"Insert-when-eligible sweep  |  delay [{min_delay}–{max_delay}]  "
        f"|  N_enc={N_ENC}  |  {N_SIM:,} sims/point",
        fontsize=11)
    p = df['p_high'].values

    # Panel 1: old/old trial yield
    ax = axes[0]
    ax.fill_between(p,
                    df['n_old_mean'] - df['n_old_std'],
                    df['n_old_mean'] + df['n_old_std'],
                    alpha=0.2, color='C0')
    ax.plot(p, df['n_old_mean'], 'o-', color='C0', label='mean')
    ax.plot(p, df['n_old_min'],  '^:', color='C0', alpha=0.5, label='min across sims')
    ax.axhline(N_ENC / 2, color='gray', lw=0.8, ls='--',
               label=f'theoretical max (={N_ENC//2})')
    ax.set_xlabel('p(choose H in encoding)', fontsize=10)
    ax.set_ylabel('Old/old trials inserted', fontsize=10)
    ax.set_title('Retrieval trial yield', fontsize=10)
    ax.legend(fontsize=8)

    # Panel 2: total sequence length
    ax = axes[1]
    ax.plot(p, df['total_mean'], 'o-', color='C1')
    ax.axhline(N_ENC, color='gray', lw=0.8, ls='--', label=f'enc-only baseline ({N_ENC})')
    ax.set_xlabel('p(choose H in encoding)', fontsize=10)
    ax.set_ylabel('Total trials (enc + ret)', fontsize=10)
    ax.set_title('Total sequence length', fontsize=10)
    ax.legend(fontsize=8)

    # Panel 3: type balance
    ax = axes[2]
    ax.plot(p, df['type1_mean'], 'o-',  label='Type 1 (H=$0,L=$1)')
    ax.plot(p, df['type2_mean'], 's--', label='Type 2 (H=$1,L=$0)')
    ax.plot(p, df['type3_mean'], '^:',  label='Type 3 (both=$0)')
    ax.plot(p, df['type4_mean'], 'd-',  label='Type 4 (both=$1)')
    ax.set_xlabel('p(choose H in encoding)', fontsize=10)
    ax.set_ylabel('Mean count per type', fontsize=10)
    ax.set_title('Retrieval type balance', fontsize=10)
    ax.legend(fontsize=7)

    plt.tight_layout()
    out = Path(out_dir) / f'sim_insert_delay{min_delay}-{max_delay}.png'
    fig.savefig(out, dpi=150); plt.show()
    print(f"Figure saved → {out}")


def plot_window_sweep(df, p_high, out_dir):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.suptitle(
        f"Delay window sweep  |  insert-when-eligible  "
        f"|  p_high={p_high}  |  {N_SIM:,} sims/point", fontsize=11)
    labels = [f"[{r.min_delay},{r.max_delay}]\nW={r.window_width}" for _, r in df.iterrows()]
    x = np.arange(len(df))

    ax = axes[0]
    ax.bar(x, df['n_old_mean'], yerr=df['n_old_std'], capsize=4, color='C0', alpha=0.7)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel('Old/old trials inserted (mean ± SD)'); ax.set_title('Retrieval yield')

    ax = axes[1]
    ax.plot(x, df['type_min_mean'], 'o-',  color='C2', label='mean of rarest type')
    ax.plot(x, df['type_min_p10'],  's--', color='C2', alpha=0.6, label='10th pct')
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel('Count of rarest retrieval type'); ax.set_title('Type balance')
    ax.legend(fontsize=8)

    plt.tight_layout()
    out = Path(out_dir) / f'sim_window_insert_phigh{p_high:.2f}.png'
    fig.savefig(out, dpi=150); plt.show()
    print(f"Figure saved → {out}")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--n_sim',        type=int, default=N_SIM)
    parser.add_argument('--min_delay',    type=int, default=MIN_DELAY)
    parser.add_argument('--max_delay',    type=int, default=MAX_DELAY)
    parser.add_argument('--seed',         type=int, default=SEED)
    parser.add_argument('--out_dir',      type=str, default='.')
    parser.add_argument('--sweep_windows',action='store_true',
                        help='Also compare several delay window sizes at p_high=0.5 and 0.7')
    args = parser.parse_args()

    p_high_values = np.round(np.arange(0.50, 1.01, 0.05), 2)

    print(f"\nInsert-when-eligible simulation")
    print(f"  N_enc={N_ENC}, delay=[{args.min_delay},{args.max_delay}], "
          f"{args.n_sim:,} sims/level\n")

    df = run_sweep(p_high_values, args.n_sim, args.min_delay, args.max_delay, args.seed)

    pd.set_option('display.float_format', '{:.2f}'.format)
    pd.set_option('display.width', 160)

    print("── p_high sweep: trial yield & type balance ───────────────────────────────")
    print(df[['p_high','n_old_mean','n_old_std','n_old_min','total_mean','old_pct_mean',
              'type1_mean','type2_mean','type3_mean','type4_mean',
              'type_min_mean','type_min_p10']].to_string(index=False))
    print()

    print("── p_high sweep: delay bias (H − L, positive = H waits longer) ────────────")
    print(df[['p_high',
              'delay_H_mean','delay_L_mean',
              'delay_diff_mean','delay_diff_std',
              'delay_diff_p5','delay_diff_p95']].to_string(index=False))
    print()

    plot_delay_bias(df, args.min_delay, args.max_delay, args.out_dir)
    plot_p_sweep(df, args.min_delay, args.max_delay, args.out_dir)

    if args.sweep_windows:
        window_configs = [
            (5, 12), (5, 15), (5, 20),
            (7, 15), (7, 20), (7, 25),
            (10, 20), (10, 25), (10, 30),
        ]
        for p_h in [0.5, 0.7]:
            print(f"Window sweep at p_high={p_h} …")
            df_w = run_window_sweep(window_configs, p_h, args.n_sim, args.seed)
            print(df_w.to_string(index=False))
            print()
            plot_window_sweep(df_w, p_h, args.out_dir)


if __name__ == '__main__':
    main()
