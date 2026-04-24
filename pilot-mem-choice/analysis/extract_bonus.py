import pandas as pd
import glob
import os
import argparse

def process_data(data_dir):
    all_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not all_files:
        print("No CSV files found in the data directory.")
        return

    results = []

    for file in all_files:
        try:
            df = pd.read_csv(file)
            
            # Find the summary row with the pre-calculated bonus
            summary = df[df['is_summary'].astype(str).str.lower() == 'true']
            
            if summary.empty:
                print(f"Skipping {file}: No summary row found (participant may not have finished).")
                continue

            # Identify participant ID (Prolific PID preferred)
            p_id = df['prolific_id'].dropna().unique()
            if len(p_id) == 0 or p_id[0] == 'local':
                p_id = df['subject_id'].dropna().unique()
            
            id_val = p_id[0] if len(p_id) > 0 else os.path.basename(file)
            bonus_val = summary['final_bonus'].values[0]

            results.append({
                'prolific_id': id_val,
                'bonus_amount': bonus_val
            })
            
        except Exception as e:
            print(f"Error processing {file}: {e}")

    if results:
        final_df = pd.DataFrame(results)
        
        # Save Prolific-specific format (PID and Bonus only, no headers)
        final_df.to_csv('prolific_bonuses.csv', index=False, header=False)
        
        # Save a readable version for the researcher
        # final_df.to_csv('bonus_summary_readable.csv', index=False)
        
        # print("\n--- Bonus Extraction Complete ---")
        # print(final_df)
        print(f"\nSaved Prolific import file to 'prolific_bonuses.csv' (No headers, ready for bulk upload)")
        # print(f"Saved readable summary to 'bonus_summary_readable.csv'")
    else:
        print("No valid results were processed.")

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description='Extract bonuses from finished JSPsych experiment sessions.')
    # parser.add_argument('--dir', type=str, default='.', help='Directory containing the data CSVs')
    
    # args = parser.parse_args()
    process_data('data')
