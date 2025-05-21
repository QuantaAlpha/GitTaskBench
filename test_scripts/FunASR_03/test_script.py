import argparse
import jieba
import re
import json
from jiwer import compute_measures
from datetime import datetime
import os


def parse_args():
    """Parse command line arguments to get output file, ground truth file, result file path and WER threshold"""
    parser = argparse.ArgumentParser(description="Evaluate text similarity between FunASR output and ground truth")
    parser.add_argument('--output', default='output.txt', help='FunASR output file path')
    parser.add_argument('--groundtruth', default='gt.txt', help='Ground truth file path')
    parser.add_argument('--result', default='eval_results.jsonl', help='JSONL file path to save evaluation results')
    parser.add_argument('--wer_threshold', type=float, default=0.3,
                        help='WER threshold, task considered successful if below this value')
    parser.add_argument('--punctuation_threshold', type=float, default=0.7,
                        help='Punctuation matching threshold, task considered failed if below this value')
    return parser.parse_args()


def preprocess_text(text):
    """Preprocess text: remove punctuation and spaces, tokenize with jieba"""
    text = re.sub(r'[^\w\s]', '', text)
    text = text.replace(" ", "")
    return " ".join(jieba.cut(text))


def extract_punctuation(text):
    """Extract punctuation from text"""
    return re.findall(r'[^\w\s]', text)


def load_text(file_path, is_output=False):
    """Load text file, extract 'text' field from FunASR output when is_output=True"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                raise ValueError(f"File {file_path} is empty")

            if is_output:
                match = re.search(r"'text':\s*'([^']*)'", content)
                if match:
                    return preprocess_text(match.group(1)), match.group(1)  # Return preprocessed text and raw text
                else:
                    raise ValueError(f"Cannot extract 'text' field from {file_path}")
            else:
                return preprocess_text(content), content  # Return preprocessed text and raw text
    except FileNotFoundError:
        return "", False
    except Exception as e:
        return "", False


def evaluate(output_file, gt_file, result_file, wer_threshold, punctuation_threshold):
    """Evaluate output file against ground truth using WER and punctuation matching, save results to JSONL"""
    # Initialize logs and results
    comments = []
    process_success = False
    result_success = False

    # Load and preprocess text
    output_text, output_raw = load_text(output_file, is_output=True)
    gt_text, gt_raw = load_text(gt_file, is_output=False)

    # Check file validity
    if output_text and gt_text:
        process_success = True
        comments.append("Input files exist, are non-empty and correctly formatted")
    else:
        comments.append("Input file issues:")
        if not output_text:
            comments.append(f"Output file {output_file} does not exist or has incorrect format")
        if not gt_text:
            comments.append(f"Ground truth file {gt_file} does not exist or has incorrect format")

    # Calculate evaluation metrics (only if files are valid)
    wer_score = None
    punctuation_match_score = None

    if process_success:
        try:
            # Calculate WER
            measures = compute_measures(gt_text, output_text)
            wer_score = measures['wer']

            # Calculate punctuation matching score
            output_punctuation = extract_punctuation(output_raw)
            gt_punctuation = extract_punctuation(gt_raw)
            punctuation_match_score = sum([1 for p in output_punctuation if p in gt_punctuation]) / max(
                len(output_punctuation), 1)

            # Record evaluation results
            comments.append(f"Word Error Rate (WER): {wer_score:.4f}")
            comments.append(f"Punctuation matching score: {punctuation_match_score:.4f}")

            # Determine task success
            if wer_score <= wer_threshold and punctuation_match_score >= punctuation_threshold:
                result_success = True
                comments.append(f"Task completed successfully (both WER and punctuation meet thresholds)")
            else:
                result_success = False
                comments.append(
                    f"Task failed (WER {'above' if wer_score > wer_threshold else 'below'} threshold {wer_threshold}, punctuation matching {'below' if punctuation_match_score < punctuation_threshold else 'meets'} threshold {punctuation_threshold})")
        except Exception as e:
            comments.append(f"Exception occurred during evaluation: {str(e)}")
    else:
        comments.append("Evaluation not performed due to invalid input files")

    # Print to console
    for comment in comments:
        print(comment)

    # Save results to JSONL
    result_entry = {
        "Process": process_success,
        "Result": result_success,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": "; ".join(comments)
    }

    try:
        with open(result_file, 'a', encoding='utf-8') as f:
            json.dump(result_entry, f, ensure_ascii=False, default=str)
            f.write('\n')
    except Exception as e:
        print(f"Error: Failed to save results to {result_file} - {str(e)}")


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    # Run evaluation
    evaluate(args.output, args.groundtruth, args.result, args.wer_threshold, args.punctuation_threshold)