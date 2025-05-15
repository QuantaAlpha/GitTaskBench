import argparse
import csv
import os
import json
from datetime import datetime


def check_file_valid(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ 文件为空: {file_path}")
        return False
    return True


def evaluate_scraping(pred_file: str, gt_file: str, threshold: float = 0.95, result_file: str = None):
    process_success = check_file_valid(pred_file) and check_file_valid(gt_file)

    if not process_success:
        result = {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": f"❌ 文件不存在或为空: pred={pred_file}, gt={gt_file}"
        }
        if result_file:
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
        return False

    # 读取预测文件
    preds = []
    with open(pred_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            preds.append(row)

    # 读取标准答案
    gts = []
    with open(gt_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gts.append(row)

    if len(preds) != len(gts):
        print(f"⚠️ 预测结果与标准答案数量不一致（预测 {len(preds)} 条，真实 {len(gts)} 条），按最小数量进行比较。")
    
    num_samples = min(len(preds), len(gts))

    fields = preds[0].keys()  # 假设列名一致
    correct_counts = {field: 0 for field in fields}

    # 按列统计正确率
    for i in range(num_samples):
        for field in fields:
            if preds[i][field] == gts[i][field]:
                correct_counts[field] += 1

    accuracies = {field: correct_counts[field] / num_samples for field in fields}

    # 打印每列准确率
    for field, acc in accuracies.items():
        print(f"字段 '{field}' 的准确率: {acc:.4f}")

    # 判断是否所有字段都超过 threshold
    success = all(acc >= threshold for acc in accuracies.values())

    if success:
        print("✅ 验证通过: 所有列准确度大于95%")
    else:
        print("❌ 验证不通过: 存在列准确度小于95%")

    # 保存结果
    if result_file:
        result = {
            "Process": True,
            "Result": success,
            "TimePoint": datetime.now().isoformat(),
            "comments": f"字段级准确率: {accuracies}, {'满足' if success else '不满足'} 95% 阈值"
        }
        with open(result_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")

    return accuracies, success


def main():
    parser = argparse.ArgumentParser(description="评估 Scrapy 抓取结果的字段级准确率")
    parser.add_argument('--output', type=str, required=True, help="预测结果（CSV）路径")
    parser.add_argument('--groundtruth', type=str, required=True, help="标注数据（CSV）路径")
    parser.add_argument('--threshold', type=float, default=0.95, help="字段准确度阈值")
    parser.add_argument('--result', type=str, required=False, help="保存结果的JSONL文件路径")

    args = parser.parse_args()

    evaluate_scraping(args.output, args.groundtruth, args.threshold, args.result)


if __name__ == "__main__":
    main()