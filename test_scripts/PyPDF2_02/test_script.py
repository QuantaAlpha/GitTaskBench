import argparse
import os
import json
import datetime
from pypdf import PdfReader
import glob
import re

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        # Uniformly remove whitespace and newlines for easier comparison
        return text.replace("\n", "").replace(" ", "")
    except Exception as e:
        return f"[ERROR] {str(e)}"

def evaluate(split_dir, truth_dir, result_path):
    log = {
        "Process": True,
        "Result": False,
        "TimePoint": datetime.datetime.now().isoformat(),
        "comments": ""
    }

    try:
        # Get all PDF files
        split_files = glob.glob(os.path.join(split_dir, "**", "*.pdf"), recursive=True)
        truth_files = glob.glob(os.path.join(truth_dir, "**", "*.pdf"), recursive=True)

        # Build page number to file mapping
        split_map = {}
        for f in split_files:
            m = re.search(r"(\d+)", os.path.basename(f))
            if m:
                split_map[int(m.group(1))] = f
        truth_map = {}
        for f in truth_files:
            m = re.search(r"(\d+)", os.path.basename(f))
            if m:
                truth_map[int(m.group(1))] = f

        # Check if valid files exist
        if not truth_map:
            log["Process"] = False
            log["comments"] += "❌ No valid .pdf files in ground truth directory"
        if not split_map:
            log["Process"] = False
            log["comments"] += "❌ No valid .pdf files in split directory"
        if not log["Process"]:
            write_result(result_path, log)
            return

        total_pages = len(truth_map)
        passed_pages = 0
        page_logs = []

        # Evaluate each ground truth page
        for page_num in sorted(truth_map.keys()):
            truth_file = truth_map[page_num]
            split_file = split_map.get(page_num)
            if not split_file:
                page_logs.append(f"❌ Page {page_num} split file not found")
                continue

            split_text = extract_text_from_pdf(split_file)
            truth_text = extract_text_from_pdf(truth_file)

            # Handle read errors
            if isinstance(split_text, str) and split_text.startswith("[ERROR]"):
                page_logs.append(f"❌ Error reading {split_file}: {split_text}")
                continue
            if isinstance(truth_text, str) and truth_text.startswith("[ERROR]"):
                page_logs.append(f"❌ Error reading {truth_file}: {truth_text}")
                continue

            if not truth_text:
                page_logs.append(f"⚠️ Page {page_num} ground truth is empty, skipping")
                passed_pages += 1  # Empty pages count as passed
                continue

            # Calculate accuracy
            correct_chars = sum(1 for a, b in zip(split_text, truth_text) if a == b)
            accuracy = (correct_chars / len(truth_text)) * 100 if truth_text else 0

            if accuracy >= 95:
                passed_pages += 1
            else:
                page_logs.append(f"❌ Page {page_num} accuracy {accuracy:.2f}% < 95%")

        if passed_pages == total_pages:
            log["Result"] = True
            log["comments"] = f"✅ All {total_pages} pages passed accuracy >=95% check"
        else:
            log["comments"] = f"❌ {total_pages - passed_pages} pages failed accuracy requirement:\n" + "\n".join(page_logs)

    except Exception as e:
        log["Process"] = False
        log["comments"] += f"[Exception error] {str(e)}"

    print(log["comments"])
    write_result(result_path, log)


def write_result(result_path, log):
    os.makedirs(os.path.dirname(result_path) or '.', exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False, default=str) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="Path to split pages directory")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to ground truth pages directory")
    parser.add_argument("--result", type=str, required=True, help="Path to output JSONL results file")
    args = parser.parse_args()

    evaluate(args.output, args.groundtruth, args.result)