import os
import sys
import json
import argparse
from difflib import SequenceMatcher
import datetime


def check_file_exists(file_path):
    """Check if file exists and is not empty"""
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    return True, ""


def cer(ref, hyp):
    """Calculate Character Error Rate (CER)"""
    matcher = SequenceMatcher(None, ref, hyp)
    edit_ops = sum(
        [max(triple[2] - triple[1], triple[2] - triple[1])
         for triple in matcher.get_opcodes() if triple[0] != 'equal']
    )
    return edit_ops / max(len(ref), 1)


def load_transcripts(file_path):
    """Load speaker transcripts from text file"""
    transcripts = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ':' not in line:
                    continue
                speaker, text = line.split(':', 1)
                if speaker not in transcripts:
                    transcripts[speaker] = []
                transcripts[speaker].append(text)

        # Combine all transcript texts for each speaker
        for speaker in transcripts:
            transcripts[speaker] = "".join(transcripts[speaker])
    except Exception as e:
        return None, str(e)

    return transcripts, ""


def evaluate(system_output_file, ground_truth_file, cer_threshold=0.05):
    """Main evaluation function: Compare system output with ground truth, calculate CER per speaker"""
    # Check files
    process_ok, process_msg = check_file_exists(system_output_file)
    if not process_ok:
        return False, False, process_msg

    process_ok, process_msg = check_file_exists(ground_truth_file)
    if not process_ok:
        return False, False, process_msg

    # Load transcripts
    system_trans, msg = load_transcripts(system_output_file)
    if system_trans is None:
        return True, False, f"Failed to load system output: {msg}"

    ground_truth, msg = load_transcripts(ground_truth_file)
    if ground_truth is None:
        return True, False, f"Failed to load ground truth: {msg}"

    total_pass = True
    results = {}
    comments = []

    # Iterate through each speaker in ground truth
    for speaker in ground_truth:
        gt_text = ground_truth.get(speaker, "")
        sys_text = system_trans.get(speaker, "")
        score = cer(gt_text, sys_text)
        results[speaker] = score
        comments.append(f"Speaker {speaker}: CER = {score:.4f}")
        if score > cer_threshold:
            total_pass = False
            comments.append(f"Speaker {speaker}'s CER ({score:.4f}) exceeds threshold {cer_threshold}")

    return True, total_pass, "\n".join(comments)


def save_results_to_jsonl(process_ok, result_ok, comments, jsonl_file):
    """Save test results to JSONL file"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    result_data = {
        "Process": bool(process_ok),
        "Result": bool(result_ok),
        "TimePoint": current_time,
        "comments": comments
    }

    os.makedirs(os.path.dirname(jsonl_file), exist_ok=True)

    with open(jsonl_file, 'a', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, default=str)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description='Evaluate speech recognition results')
    parser.add_argument('--output', required=True, help='System output file path')
    parser.add_argument('--groundtruth', required=True, help='Ground truth file path')
    parser.add_argument('--cer_threshold', type=float, default=0.10, help='CER threshold')
    parser.add_argument('--result', required=True, help='Result JSONL file path')

    args = parser.parse_args()

    process_ok, result_ok, comments = evaluate(
        args.output,
        args.groundtruth,
        args.cer_threshold
    )

    save_results_to_jsonl(process_ok, result_ok, comments, args.result)

    if not process_ok:
        print(f"Processing failed: {comments}")
    if not result_ok:
        print(f"Results do not meet requirements: {comments}")
    print("Test completed")  # Changed from "Test passed!" to neutral prompt


if __name__ == "__main__":
    main()