import jiwer
import argparse
import os
import json
from datetime import datetime


def evaluate_speech_recognition(output_path, groundtruth_path, wer_threshold=0.3):
    """
    Evaluate speech recognition performance using WER (Word Error Rate) metric.

    Args:
        output_path (str): Path to speech recognition output text file
        groundtruth_path (str): Path to ground truth text file
        wer_threshold (float): WER threshold (default 0.3, i.e., 30%)

    Returns:
        dict: Dictionary containing WER value and evaluation results
    """

    # Read text file
    def read_text_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                # Only remove leading/trailing whitespace, preserve original format
                if not text:
                    raise ValueError(f"File is empty: {file_path}")
                return text
        except UnicodeDecodeError:
            raise ValueError(f"File encoding error, expected UTF-8: {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {str(e)}")

    # Load output and ground truth texts
    try:
        output_text = read_text_file(output_path)
        groundtruth_text = read_text_file(groundtruth_path)
    except Exception as e:
        return {
            'wer': None,
            'threshold': wer_threshold,
            'is_acceptable': False,
            'message': f"Text loading failed: {str(e)}"
        }

    # Debug: print raw texts
    print(f"Raw groundtruth: '{groundtruth_text}'")
    print(f"Raw output: '{output_text}'")

    # Verify texts are not empty
    if not groundtruth_text.strip() or not output_text.strip():
        return {
            'wer': None,
            'threshold': wer_threshold,
            'is_acceptable': False,
            'message': f"Empty text (Groundtruth: '{groundtruth_text}', Output: '{output_text}')"
        }

    # Calculate WER
    try:
        # Only lowercase conversion, preserve original word segmentation
        wer = jiwer.wer(
            groundtruth_text.lower(),
            output_text.lower()
        )
    except Exception as e:
        return {
            'wer': None,
            'threshold': wer_threshold,
            'is_acceptable': False,
            'message': f"WER calculation failed: {str(e)} (Groundtruth: '{groundtruth_text}', Output: '{output_text}')"
        }

    # Evaluation results
    is_acceptable = wer <= wer_threshold
    result = {
        'wer': float(wer),
        'threshold': float(wer_threshold),
        'is_acceptable': is_acceptable,
        'message': f"WER: {wer * 100:.2f}%, {'Acceptable' if is_acceptable else 'Unacceptable'} (Threshold: {wer_threshold * 100:.2f}%)"
    }

    return result


def check_file_validity(file_path):
    """Check if file exists, is not empty, and has correct format"""
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    if not file_path.endswith('.txt'):
        return False, f"Invalid file format, expected .txt: {file_path}"
    return True, ""


def main():
    parser = argparse.ArgumentParser(description="Evaluate speech recognition using WER metric.")
    parser.add_argument('--output', type=str, required=True, help="Path to the speech recognition output text file")
    parser.add_argument('--groundtruth', type=str, required=True, help="Path to the groundtruth text file")
    parser.add_argument('--threshold', type=float, default=0.3, help="WER threshold (default: 0.3, i.e., 30%)")
    parser.add_argument('--result', type=str, default=None, help="Path to JSONL file to store results")

    args = parser.parse_args()

    # Check file validity
    comments = []
    process_success = True
    for path in [args.output, args.groundtruth]:
        is_valid, comment = check_file_validity(path)
        if not is_valid:
            process_success = False
            comments.append(comment)

    # Initialize result dictionary
    result_dict = {
        "Process": process_success,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }

    # If Process failed, save results directly
    if not process_success:
        result_dict["comments"] = "; ".join(comments)
    else:
        try:
            # Run evaluation
            result = evaluate_speech_recognition(
                output_path=args.output,
                groundtruth_path=args.groundtruth,
                wer_threshold=args.threshold
            )

            # Update results
            result_dict["Result"] = result['is_acceptable']
            result_dict["comments"] = result['message']
            print(result['message'])
        except Exception as e:
            result_dict["Result"] = False
            result_dict["comments"] = f"Evaluation failed: {str(e)}"
            comments.append(str(e))

    # If result file path specified, save to JSONL
    if args.result:
        try:
            # Ensure proper boolean serialization
            serializable_dict = {
                "Process": bool(result_dict["Process"]),
                "Result": bool(result_dict["Result"]),
                "TimePoint": result_dict["TimePoint"],
                "comments": result_dict["comments"]
            }
            with open(args.result, 'a', encoding='utf-8') as f:
                json_line = json.dumps(serializable_dict, ensure_ascii=False)
                f.write(json_line + '\n')
        except Exception as e:
            print(f"Failed to save results to {args.result}: {str(e)}")
            raise  # Raise exception to ensure non-zero exit code


if __name__ == "__main__":
    main()