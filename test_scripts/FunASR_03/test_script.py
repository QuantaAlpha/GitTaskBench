import argparse
import jieba
import re
import json
from jiwer import compute_measures
from datetime import datetime
import os
from collections import Counter


def parse_args():
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
    """Extract punctuation characters from text"""
    return re.findall(r'[^\w\s]', text)


def punctuation_match_score(output_puncs, gt_puncs):
    """Compute matching score based on overlapping punctuation"""
    output_counter = Counter(output_puncs)
    gt_counter = Counter(gt_puncs)
    common = sum((output_counter & gt_counter).values())
    total = max(len(gt_puncs), 1)
    return common / total


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
                    extracted_text = match.group(1)
                else:
                    extracted_text = content
                return preprocess_text(extracted_text), extracted_text
            else:
                return preprocess_text(content), content
    except FileNotFoundError:
        return "", False
    except Exception as e:
        return "", False



def evaluate(output_file, gt_file, result_file, wer_threshold, punctuation_threshold):
    comments = []
    process_success = False
    result_success = False

    output_text, output_raw = load_text(output_file, is_output=True)
    gt_text, gt_raw = load_text(gt_file, is_output=False)

    if output_text and gt_text:
        process_success = True
        comments.append("Input files exist, are non-empty and correctly formatted")
    else:
        comments.append("Input file issues:")
        if not output_text:
            comments.append(f"Output file {output_file} does not exist or has incorrect format")
        if not gt_text:
            comments.append(f"Ground truth file {gt_file} does not exist or has incorrect format")

    wer_score = None
    punctuation_score = None

    if process_success:
        try:
            measures = compute_measures(gt_text, output_text)
            wer_score = measures['wer']

            output_puncs = extract_punctuation(output_raw)
            gt_puncs = extract_punctuation(gt_raw)
            punctuation_score = punctuation_match_score(output_puncs, gt_puncs)

            comments.append(f"Word Error Rate (WER): {wer_score:.4f}")
            comments.append(f"Punctuation matching score: {punctuation_score:.4f}")

            if wer_score <= wer_threshold and punctuation_score >= punctuation_threshold:
                result_success = True
                comments.append("Task completed successfully (WER and punctuation both meet thresholds)")
            else:
                comments.append(
                    f"Task failed (WER {'above' if wer_score > wer_threshold else 'below'} threshold {wer_threshold}, "
                    f"punctuation {'below' if punctuation_score < punctuation_threshold else 'meets'} threshold {punctuation_threshold})"
                )
        except Exception as e:
            comments.append(f"Exception occurred during evaluation: {str(e)}")
    else:
        comments.append("Evaluation not performed due to invalid input files")

    for c in comments:
        print(c)

    result_entry = {
        "Process": process_success,
        "Result": result_success,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": "; ".join(comments)
    }

    try:
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        with open(result_file, 'a', encoding='utf-8') as f:
            json.dump(result_entry, f, ensure_ascii=False, default=str)
            f.write('\n')
    except Exception as e:
        print(f"Error saving result to {result_file}: {str(e)}")


if __name__ == "__main__":
    args = parse_args()
    evaluate(args.output, args.groundtruth, args.result, args.wer_threshold, args.punctuation_threshold)
