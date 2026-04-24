"""General script for extracting bonuses from jsPsych data for Prolific payments"""

import pandas as pd
import glob
import os
import argparse

def process_data(data_dir):
    all_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not all_files:
        print(f"No CSV files found in directory: {data_dir}")
        return

    results = []

    for file in all_files:
        try:
            df = pd.read_csv(file)
            
            # Find the summary row with the pre-calculated bonus
            # Support both boolean and string versions of 'true'
            if 'is_summary' not in df.columns:
                print(f"Skipping {file}: Missing 'is_summary' column.")
                continue
                
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
        output_file = 'prolific_bonuses.csv'
        final_df.to_csv(output_file, index=False, header=False)
        print(f"\nSuccessfully processed {len(results)} files.")
        print(f"Saved Prolific import file to '{output_file}' (No headers, ready for bulk upload)")
    else:
        print("No valid finished sessions found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract bonuses from finished JSPsych experiment sessions.')
    parser.add_argument('--dir', type=str, default='data', help='Directory containing the data CSVs (default: data)')
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.exists(args.dir):
        # Fallback to current dir if 'data' doesn't exist
        if args.dir == 'data':
            process_data('.')
        else:
            print(f"Error: Directory '{args.dir}' not found.")
    else:
        process_data(args.dir)
