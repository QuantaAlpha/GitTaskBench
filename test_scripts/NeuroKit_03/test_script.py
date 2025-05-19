import pandas as pd
import numpy as np
import json
import argparse
import os
from datetime import datetime
import traceback
from io import StringIO
import sys

def evaluate_rsp_metrics(output_csv, ground_truth_csv):
    log_output = StringIO()
    sys_stdout = sys.stdout
    sys.stdout = log_output  # 捕获print输出
    result = {
        "Process": False,
        "Result": False,
        "TimePoint": datetime.now().isoformat(),
        "comments": ""
    }

    try:
        # 验证输入文件
        if not os.path.exists(output_csv):
            print(f"Error: Output CSV file '{output_csv}' does not exist")
            return result
        if not os.path.exists(ground_truth_csv):
            print(f"Error: Ground truth CSV file '{ground_truth_csv}' does not exist")
            return result
        if os.path.getsize(output_csv) == 0:
            print(f"Error: Output CSV file '{output_csv}' is empty")
            return result
        if os.path.getsize(ground_truth_csv) == 0:
            print(f"Error: Ground truth CSV file '{ground_truth_csv}' is empty")
            return result
        result["Process"] = True

        # 加载 CSV 文件
        output_df = pd.read_csv(output_csv)
        gt_df = pd.read_csv(ground_truth_csv)

        # 验证必要列
        required_columns = ["Mean_Respiratory_Rate_BPM", "Number_of_Peaks", "Peak_Times_Seconds"]
        for df, name in [(output_df, "Output"), (gt_df, "Ground Truth")]:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                print(f"Error: {name} CSV missing columns: {missing_cols}")
                return result

        # 提取指标
        pred_rate = output_df["Mean_Respiratory_Rate_BPM"].iloc[0]
        pred_peaks = json.loads(output_df["Peak_Times_Seconds"].iloc[0])
        pred_count = output_df["Number_of_Peaks"].iloc[0]

        gt_rate = gt_df["Mean_Respiratory_Rate_BPM"].iloc[0]
        gt_peaks = json.loads(gt_df["Peak_Times_Seconds"].iloc[0])
        gt_count = gt_df["Number_of_Peaks"].iloc[0]

        # 评估指标
        rate_mae = abs(pred_rate - gt_rate) if not np.isnan(pred_rate) and not np.isnan(gt_rate) else np.nan
        rate_success = rate_mae <= 1.0 if not np.isnan(rate_mae) else False

        if pred_peaks and gt_peaks:
            peak_errors = [min(abs(p - gt) for gt in gt_peaks) for p in pred_peaks]
            peak_mptd = sum(peak_errors) / len(peak_errors) if peak_errors else np.nan
            peak_matching_count = sum(1 for err in peak_errors if err <= 0.1)
            peak_matching_rate = peak_matching_count / len(pred_peaks) if pred_peaks else 0.0
        else:
            peak_mptd = np.nan
            peak_matching_rate = 0.0
        peak_success = (peak_mptd <= 0.1 and peak_matching_rate >= 0.8) if not np.isnan(peak_mptd) else False

        peak_count_relative_error = (
            abs(pred_count - gt_count) / gt_count if gt_count > 0 else np.nan
        )
        count_success = peak_count_relative_error <= 0.1 if not np.isnan(peak_count_relative_error) else False

        success = rate_success and peak_success and count_success
        result["Result"] = success

        print("Evaluation Results:")
        print(f"Rate MAE: {rate_mae:.2f} BPM (Success: {rate_success})")
        print(f"Peak MPTD: {peak_mptd:.3f} seconds (Success: {peak_success})")
        print(f"Peak Matching Rate: {peak_matching_rate:.2f}")
        print(f"Peak Count Relative Error: {peak_count_relative_error:.2f} (Success: {count_success})")
        print(f"Overall Success: {success}")

    except Exception as e:
        traceback.print_exc(file=log_output)

    finally:
        sys.stdout = sys_stdout  # 恢复 stdout
        result["comments"] = log_output.getvalue()
        return result

def main():
    parser = argparse.ArgumentParser(description="Evaluate RSP metrics against ground truth")
    parser.add_argument("--output", required=True, help="Path to output CSV file (rsp_metrics.csv)")
    parser.add_argument("--groundtruth", required=True, help="Path to ground truth CSV file")
    parser.add_argument("--result", default="results.jsonl", help="Path to JSONL result file")
    args = parser.parse_args()

    result_data = evaluate_rsp_metrics(args.output, args.groundtruth)

    # 结果写入 JSONL 文件
    try:
        with open(args.result, "a", encoding='utf-8') as f:
            f.write(json.dumps(result_data, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        print(f"Failed to write result to {args.result}: {e}")

if __name__ == "__main__":
    main()
