import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from scipy.stats import sem
import glob
import os

# Set Plotting Style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Inter', 'Arial']

def analyze_task_ei(data_path='data/*.csv'):
    files = glob.glob(data_path)
    if not files:
        print("No data files found.")
        return

    # 1. Load and Clean Data
    dfs = []
    for f in files:
        try:
            temp_df = pd.read_csv(f)
            # Ensure is_trial is boolean
            if 'is_trial' in temp_df.columns:
                if temp_df['is_trial'].dtype == object:
                    temp_df['is_trial'] = temp_df['is_trial'].astype(str).str.lower() == 'true'
                elif temp_df['is_trial'].dtype != bool:
                    temp_df['is_trial'] = temp_df['is_trial'].astype(bool)
                temp_df = temp_df[temp_df['is_trial'] == True].copy()
                dfs.append(temp_df)
        except Exception as e:
            print(f"Error loading {f}: {e}")
    
    if not dfs:
        print("No valid trial data found in CSVs.")
        return
        
    df = pd.concat(dfs, ignore_index=True)
    df = df.dropna(subset=['chosen_color', 'is_lucky'])
    
    # Robust numeric conversion
    for col in ['is_lucky', 'reward', 'old_reward', 'did_choose_old', 'trials_since_reversal']:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = pd.to_numeric(df[col].astype(str).replace({'true': 1, 'false': 0, 'True': 1, 'False': 0}), errors='coerce')
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce')

    # 2. Check for episodic logging
    has_episodic = 'did_choose_old' in df.columns and 'old_reward' in df.columns

    # 3. Process Reversals for Learning Curve (Plot B)
    # If the CSV has 'trials_since_reversal', we use it to find the window.
    # Otherwise we'll calculate it using the color-luck toggle heuristic.
    
    def get_reversal_relative(subject_df):
        subject_df = subject_df.sort_values('trial_i')
        
        # Method 1: Use logged trials_since_reversal if available
        if 'trials_since_reversal' in subject_df.columns:
            # Reversals are points where trials_since_reversal is 0
            rev_indices = subject_df[subject_df['trials_since_reversal'] == 0].index.tolist()
        else:
            # Method 2: Heuristic
            subject_df['lucky_color_at_trial'] = np.where(
                ((subject_df['chosen_color'] == 'blue') & (subject_df['is_lucky'] == 1)) | 
                ((subject_df['chosen_color'] == 'orange') & (subject_df['is_lucky'] == 0)),
                'blue', 'orange'
            )
            subject_df['is_reversal'] = (subject_df['lucky_color_at_trial'] != subject_df['lucky_color_at_trial'].shift()).fillna(False)
            rev_indices = subject_df[subject_df['is_reversal']].index.tolist()
        
        rel_data = []
        for rev_idx in rev_indices:
            pos = subject_df.index.get_loc(rev_idx)
            for offset in range(-5, 6):
                idx = pos + offset
                if 0 <= idx < len(subject_df):
                    row = subject_df.iloc[idx].copy()
                    row['trial_relative'] = offset
                    rel_data.append(row)
        return pd.DataFrame(rel_data) if rel_data else pd.DataFrame()

    reversal_plot_df = df.groupby('subject_id', group_keys=False).apply(get_reversal_relative).reset_index(drop=True)

    # --- FIGURE: BEHAVIORAL DASHBOARD ---
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    plt.subplots_adjust(hspace=0.3, wspace=0.25)
    
    # PLOT A: Episodic Influence
    if has_episodic:
        old_trials = df[df['is_old_trial'] == True].copy()
        sns.pointplot(data=old_trials, x='old_reward', y='did_choose_old', hue='stim_type', 
                      errorbar='se', capsize=.1, markers=["o", "s"], linestyles=["-", "--"], ax=axes[0, 0])
        axes[0, 0].set_title('Episodic Influence by Stimulus Type', fontsize=16, fontweight='bold')
        axes[0, 0].set_ylabel('P(Choose Old Object)', fontsize=12)
        axes[0, 0].set_xlabel('Previous Reward Value of Object', fontsize=12)
        axes[0, 0].set_ylim(-0.05, 1.05)
        axes[0, 0].legend(title='Condition')
    else:
        axes[0, 0].text(0.5, 0.5, "Awaiting New Data Structure...", ha='center', va='center', color='gray', fontsize=14)
        axes[0, 0].set_title('Episodic Influence (No Data)', fontsize=16, fontweight='bold')

    # PLOT B: Reversal Performance
    if not reversal_plot_df.empty:
        sns.lineplot(data=reversal_plot_df, x='trial_relative', y='is_lucky', 
                     marker='o', markersize=8, linewidth=2, color='#9b59b6', errorbar='se', ax=axes[0, 1])
        axes[0, 1].axvline(0, color='red', linestyle='--', alpha=0.5, label='Reversal')
        axes[0, 1].set_title('Learning Curve Around Reversals', fontsize=16, fontweight='bold')
        axes[0, 1].set_ylabel('P(Choose Lucky Deck)', fontsize=12)
        axes[0, 1].set_xlabel('Trials Relative to Reversal', fontsize=12)
        axes[0, 1].set_xticks(range(-5, 6))
        axes[0, 1].set_ylim(0, 1)
        axes[0, 1].grid(True, linestyle=':', alpha=0.6)
    else:
        axes[0, 1].set_title('Learning Curve Around Reversals', fontsize=16, fontweight='bold', alpha=0.5)

    # PLOT C: Overall Episodic Weight
    if has_episodic:
        ebci = df[df['is_old_trial'] == True].groupby(['subject_id', 'stim_type'])['did_choose_old'].mean().reset_index()
        sns.barplot(data=ebci, x='stim_type', y='did_choose_old', palette='coolwarm', ax=axes[1, 0], errorbar='se')
        axes[1, 0].set_title('Overall Episodic Choice Rate', fontsize=16, fontweight='bold')
        axes[1, 0].set_ylabel('Mean P(Choose Old)', fontsize=12)
        axes[1, 0].set_ylim(0, 1)
    
    # PLOT D: RT Comparison
    sns.boxplot(data=df, x='stim_type', y='rt', palette='Set2', ax=axes[1, 1])
    axes[1, 1].set_title('Reaction Time (RT)', fontsize=16, fontweight='bold')
    axes[1, 1].set_ylabel('RT (ms)', fontsize=12)

    plt.savefig('task_ei_summary.png', dpi=300, bbox_inches='tight')
    print("Dashboard saved to task_ei_summary.png")

if __name__ == "__main__":
    analyze_task_ei()
