#!/usr/bin/env python3
"""Count participants from each of the 3 tasks, using exclusion criteria. 
Uses the pre-made data CSVs from `combine_data.py`

Usage: python episodic-choice-task/scripts/count_participants.py

Prints output.
"""
import os
import pandas as pd
from scipy.stats import ttest_1samp

DATA_DIR = '/Users/chrisiyer/_Current/lab/code/value-associability/episodic-choice-task/data'


def subject_sig_above_chance(g):
    _, p = ttest_1samp(g['optimal_old_choice'], 0.5, alternative='greater')
    return p < 0.05

def count_participants_task(path):

    print('----------------------------------')
    if 'mixed' in path:
        print("Beginning mixed-memorability...")
    elif 'matched' in path:
        print("Beginning matched-memorability...")
    else:
        print("Beginning main task...")
    
    try:
        df = pd.read_csv(path)
    except:
        print(f"     data file not found, skipping...")
        return (0,0)

    ##### filter out AI responses
    attention_df = df.query('is_attention_check == True').copy()

    # the very first pilot had the AI press space bar, all others used X key
    space_df = attention_df.query(' experiment_id == "episodic_choice_v3" and response_key == " " ')
    x_df = attention_df.query('experiment_id != "episodic_choice_v3" and (response_key == "x" or response == "x") ')

    ai_df = pd.concat([space_df, x_df])
    AI_PIDS = ai_df['participant_id'].unique().tolist()
    if len(AI_PIDS) > 0:
        print(f"     {len(AI_PIDS)} AI agent(s) detected! PIDS:")
        for pid in AI_PIDS:
            print(f"          {pid}")
    
    ##### filter out attention check failures
    attn_perf = attention_df.groupby('participant_id', as_index=False).agg({'correct': 'mean'})
    FAILED_ATTN_PIDS = attn_perf.query('correct < 1')['participant_id'].tolist()
    print(f"     {len(FAILED_ATTN_PIDS)} failed at least 1 attention check")

    ##### filter out chance-level performance
    old_trials_df = df.query('old_trial == 1').dropna(subset=['optimal_old_choice']).copy()
    ttest_df = old_trials_df.groupby('participant_id').apply(subject_sig_above_chance, include_groups=False).reset_index()
    AT_CHANCE_PIDS = ttest_df.participant_id[~ttest_df[0]].unique().tolist()
    print(f"     {len(AT_CHANCE_PIDS)} failed to pass t-test from chance")

    ##### filter out incomplete data (mixed/matched only, mirrors analysis.ipynb)
    INCOMPLETE_PIDS = []
    if 'mixed' in path or 'matched' in path:
        INCOMPLETE_PIDS = df[df.old_trial == 1].groupby('participant_id').size().loc[lambda s: s < 70].index.tolist()
        print(f"     {len(INCOMPLETE_PIDS)} had incomplete data (< 70 old trials)")

    #### final count
    total = len(df.participant_id.unique())
    ALL_EXCLUDED = set(AI_PIDS + FAILED_ATTN_PIDS + AT_CHANCE_PIDS + INCOMPLETE_PIDS)
    included = len([p for p in df.participant_id.unique() if p not in ALL_EXCLUDED])

    return (total, included)


def count_participants():
    counts_main = count_participants_task(os.path.join(DATA_DIR, 'episodic_choice_data.csv'))
    counts_mixed = count_participants_task(os.path.join(DATA_DIR, 'episodic_choice_data-mixed_memorability.csv'))
    counts_matched = count_participants_task(os.path.join(DATA_DIR, 'episodic_choice_data-matched_memorability.csv'))
    
    rows = [("Main", *counts_main), ("Mixed", *counts_mixed), ("Matched", *counts_matched)]
    print("----------------------------------\n")
    print("     ===== Participant counts =====")
    print(f" | {'Task':<8} | {'N (all)':>8} | {'N (included)':>13} |")
    print(f" |{'-'*10}|{'-'*10}|{'-'*15}|")
    for task, total, included in rows:
        print(f" | {task:<8} | {total:>8} | {included:>13} |")


if __name__ == "__main__":
    count_participants()
