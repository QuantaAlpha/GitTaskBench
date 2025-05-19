#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np
import json
import os
import sys
import datetime


def parse_array_string(array_str):
    """
    Parse a string representation of an array into a list of floats or ints
    Handles various formats: [1,2,3], [ 1, 2, 3], etc.
    """
    if not isinstance(array_str, str):
        return array_str
    
    # Remove brackets and split by comma
    try:
        # Try parsing as JSON first (handles most cases cleanly)
        return json.loads(array_str.replace("'", "\""))
    except:
        # Fallback parsing method
        cleaned = array_str.strip()
        if cleaned.startswith('[') and cleaned.endswith(']'):
            cleaned = cleaned[1:-1]
            
        # Split by comma and convert to appropriate numeric type
        if cleaned:
            values = [val.strip() for val in cleaned.split(',')]
            
            # Try to convert to numbers
            result = []
            for val in values:
                try:
                    # Try integer first
                    result.append(int(val))
                except ValueError:
                    try:
                        # Then try float
                        result.append(float(val))
                    except ValueError:
                        # If not a number, keep as string
                        result.append(val)
            return result
        return []


def normalize_dataframe(df):
    """
    Normalize a dataframe by ensuring all array values are actual lists
    """
    for col in df.columns:
        df[col] = df[col].apply(parse_array_string)
    return df


def array_equals(arr1, arr2, rtol=0.1, atol=10):
    """
    Compare two arrays (lists) for approximate equality
    For numeric values, uses np.isclose; for others, uses direct comparison
    """
    if len(arr1) != len(arr2):
        return False
    
    for a, b in zip(arr1, arr2):
        # For numeric values, use np.isclose
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not np.isclose(a, b, rtol=rtol, atol=atol):
                return False
        # For other types, direct comparison
        elif a != b:
            return False
    
    return True


def check_file_validity(file_path):
    """
    Check if a file exists, is not empty, and has valid format
    """
    # Check if file exists
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    # Check if file is not empty
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    
    # Try to read file to check format
    try:
        df = pd.read_csv(file_path, sep='\t' if file_path.endswith('.tsv') else ',')
        if df.empty:
            return False, f"File contains no data: {file_path}"
        return True, "File is valid"
    except Exception as e:
        return False, f"Invalid file format: {str(e)}"


def evaluate_scr_extraction(gt_path, output_path):
    """
    Evaluate the SCR extraction by comparing ground truth with output
    Returns a dictionary with evaluation metrics
    
    Args:
        gt_path: Path to ground truth CSV
        output_path: Path to output CSV
    """
    result = {
        "Process": True,
        "Result": False,
        "TimePoint": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }
    
    # Check if ground truth file is valid
    gt_valid, gt_message = check_file_validity(gt_path)
    if not gt_valid:
        result["Process"] = False
        result["comments"] = gt_message
        return result
    
    # Check if output file is valid
    output_valid, output_message = check_file_validity(output_path)
    if not output_valid:
        result["Process"] = False
        result["comments"] = output_message
        return result
    
    try:
        # Read the CSV files
        gt_df = pd.read_csv(gt_path, sep='\t' if gt_path.endswith('.tsv') else ',')
        output_df = pd.read_csv(output_path, sep='\t' if output_path.endswith('.tsv') else ',')
        
        # Normalize column names (case-insensitive matching)
        expected_cols = ['ECG_R_Peaks','ECG_P_Peaks']
        col_mapping = {}
        
        for col in output_df.columns:
            for expected in expected_cols:
                if expected.lower() == col.lower():
                    col_mapping[col] = expected
                    break
        
        # Rename columns to match expected format
        if col_mapping:
            output_df = output_df.rename(columns=col_mapping)
        
        # Check if all required columns are present
        missing_cols = [col for col in expected_cols if col not in output_df.columns]
        if missing_cols:
            result["comments"] = f"Missing columns in output: {', '.join(missing_cols)}"
            return result
        
        # Process both dataframes to ensure array values are parsed correctly
        gt_df = normalize_dataframe(gt_df)
        output_df = normalize_dataframe(output_df)
        
        # For each expected column, compare the values
        column_matches = {}
        overall_match = True
        comments = []
        
        for col in expected_cols:
            if col in gt_df.columns and col in output_df.columns:
                gt_val = gt_df[col].iloc[0] if not gt_df.empty else []
                out_val = output_df[col].iloc[0] if not output_df.empty else []
                
                # Compare arrays
                match = array_equals(gt_val, out_val)
                column_matches[col] = match
                
                comments.append(f"{col}: {'Match' if match else 'Mismatch'}")
                
                if not match:
                    overall_match = False
            else:
                column_matches[col] = False
                overall_match = False
                comments.append(f"{col}: Missing")
        
        # Calculate accuracy as percentage of matching columns
        matching_cols = sum(1 for match in column_matches.values() if match)
        accuracy = matching_cols / len(expected_cols) if expected_cols else 0
        accuracy_percent = accuracy * 100
        
        # Determine success based on 100% accuracy
        success = overall_match
        
        result["Result"] = success
        result["comments"] = f"Accuracy: {accuracy_percent:.2f}%, Matched columns: {matching_cols}/{len(expected_cols)}. {'; '.join(comments)}"
        
        return result
    
    except Exception as e:
        result["Process"] = True  # Files were valid, but evaluation failed
        result["Result"] = False
        result["comments"] = f"Evaluation failed: {str(e)}"
        return result


def save_result_to_jsonl(result_data, result_file):
    """
    Save result to JSONL file (append mode)
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(result_file)), exist_ok=True)
        
        # Open file in append mode, create if not exists
        with open(result_file, 'a',encoding='utf-8') as f:
            # Write the JSON object as a single line
            f.write(json.dumps(result_data) + '\n')
    except Exception as e:
        print(f"Warning: Could not save results to {result_file}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Evaluate SCR extraction from EDA data')
    parser.add_argument('--groundtruth', required=True, help='Path to ground truth CSV file')
    parser.add_argument('--output', required=True, help='Path to agent output CSV file')
    parser.add_argument('--verbose', action='store_true', help='Print detailed results')
    parser.add_argument('--result', help='Path to save result JSONL file')
    
    args = parser.parse_args()
    
    try:
        # Evaluate with standard accuracy
        results = evaluate_scr_extraction(args.groundtruth, args.output)
        
        # Print results based on verbosity
        if args.verbose:
            print(json.dumps(results, indent=2))
        else:
            print(f"Process: {results['Process']}")
            print(f"Result: {results['Result']}")
            print(f"Comments: {results['comments']}")
        
        # Save results to JSONL file if specified
        if args.result:
            save_result_to_jsonl(results, args.result)
            
    except Exception as e:
        # Catch any unexpected exceptions to ensure script continues
        error_result = {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "comments": f"Unexpected error: {str(e)}"
        }
        
        print(f"Error: {str(e)}")
        
        # Try to save error result
        if args.result:
            save_result_to_jsonl(error_result, args.result)
    
    # Always return 0 to ensure script continues in automated environments
    return 0


if __name__ == "__main__":
    main()  # Do not use sys.exit() to ensure script always completes