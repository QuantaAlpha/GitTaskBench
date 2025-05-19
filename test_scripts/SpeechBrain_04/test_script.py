import argparse
import librosa
import numpy as np
from pesq import pesq
import os
import json
from datetime import datetime

def validate_wav_file(wav_path):
    """Validates if the WAV file exists, is non-empty, and is a valid audio file."""
    try:
        # Checking if file exists
        if not os.path.exists(wav_path):
            return False, f"File {wav_path} does not exist."
        
        # Checking if file is non-empty
        if os.path.getsize(wav_path) == 0:
            return False, f"File {wav_path} is empty."
        
        # Attempting to load the file to verify it's a valid WAV
        librosa.load(wav_path, sr=16000)
        return True, "Valid WAV file."
    
    except Exception as e:
        return False, f"Invalid WAV file {wav_path}: {str(e)}"

def evaluate_speech_enhancement(input_wav, output_wav, threshold=2.0):
    # Loading audio files
    ref, sr = librosa.load(input_wav, sr=16000)  # Reference (noisy) audio
    deg, sr = librosa.load(output_wav, sr=16000)  # Enhanced (output) audio
    
    # Ensuring same length for PESQ calculation
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len]
    deg = deg[:min_len]
    
    # Calculating PESQ score (WB: Wideband, 16kHz)
    pesq_score = pesq(16000, ref, deg, 'wb')
    
    # Determining if task is successful based on threshold
    task_passed = pesq_score >= threshold
    
    return pesq_score, task_passed

def save_result_to_jsonl(process_status, result_status, comments, result_file):
    """Saves evaluation result to a JSONL file."""
    result_entry = {
        "Process": process_status,
        "Result": result_status,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": comments
    }
    print(comments)
    # Writing to JSONL file in append mode with UTF-8 encoding
    with open(result_file, 'a', encoding='utf-8') as f:
        json.dump(result_entry, f, default=str)
        f.write('\n')


def main():
    # Setting up argument parser
    parser = argparse.ArgumentParser(description='Evaluate speech enhancement using PESQ metric')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to input (noisy) wav file')
    parser.add_argument('--output', type=str, required=True, help='Path to output (enhanced) wav file')
    parser.add_argument('--threshold', type=float, default=1.5, help='PESQ threshold for task success')
    parser.add_argument('--result', type=str, required=True, help='Path to JSONL result file')
    
    args = parser.parse_args()
    
    # Validating input and output WAV files
    input_valid, input_comment = validate_wav_file(args.groundtruth)
    output_valid, output_comment = validate_wav_file(args.output)
    
    process_status = input_valid and output_valid
    comments = f"Input validation: {input_comment}; Output validation: {output_comment}"
    pesq_score = None
    task_passed = False
    
    # Proceeding with evaluation only if both files are valid
    if process_status:
        try:
            pesq_score, task_passed = evaluate_speech_enhancement(args.groundtruth, args.output, args.threshold)
            comments += f"; PESQ Score: {pesq_score:.3f}, Task Passed: {task_passed} (Threshold: {args.threshold})"
        except Exception as e:
            comments += f"; Evaluation failed: {str(e)}"
            task_passed = False
    else:
        task_passed = False
    
    # Saving result to JSONL
    save_result_to_jsonl(process_status, task_passed, comments, args.result)
    
    # Printing results
    print(f"PESQ Score: {pesq_score:.3f}" if pesq_score is not None else "Evaluation skipped due to invalid files")
    print(f"Task Passed: {task_passed} (Threshold: {args.threshold})")
    print(f"Results saved to: {args.result}")

if __name__ == "__main__":
    main()