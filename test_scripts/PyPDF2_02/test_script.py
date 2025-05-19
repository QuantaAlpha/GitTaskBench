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
        # 统一去除空白和换行，便于比较
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
        # 获取所有 PDF 文件
        split_files = glob.glob(os.path.join(split_dir, "**", "*.pdf"), recursive=True)
        truth_files = glob.glob(os.path.join(truth_dir, "**", "*.pdf"), recursive=True)

        # 构建页码到文件的映射
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

        # 检查是否存在有效文件
        if not truth_map:
            log["Process"] = False
            log["comments"] += "❌ 标准目录中没有有效的 .pdf 文件"
        if not split_map:
            log["Process"] = False
            log["comments"] += "❌ 拆分目录中没有有效的 .pdf 文件"
        if not log["Process"]:
            write_result(result_path, log)
            return

        total_pages = len(truth_map)
        passed_pages = 0
        page_logs = []

        # 对每个标准页码进行评估
        for page_num in sorted(truth_map.keys()):
            truth_file = truth_map[page_num]
            split_file = split_map.get(page_num)
            if not split_file:
                page_logs.append(f"❌ Page {page_num} 找不到拆分文件")
                continue

            split_text = extract_text_from_pdf(split_file)
            truth_text = extract_text_from_pdf(truth_file)

            # 读取错误处理
            if isinstance(split_text, str) and split_text.startswith("[ERROR]"):
                page_logs.append(f"❌ 读取 {split_file} 出错：{split_text}")
                continue
            if isinstance(truth_text, str) and truth_text.startswith("[ERROR]"):
                page_logs.append(f"❌ 读取 {truth_file} 出错：{truth_text}")
                continue

            if not truth_text:
                page_logs.append(f"⚠️ Page {page_num} 的 Ground truth 为空，跳过")
                passed_pages += 1  # 空白页也视为通过
                continue

            # 计算准确率
            correct_chars = sum(1 for a, b in zip(split_text, truth_text) if a == b)
            accuracy = (correct_chars / len(truth_text)) * 100 if truth_text else 0

            if accuracy >= 95:
                passed_pages += 1
            else:
                page_logs.append(f"❌ Page {page_num} 准确率 {accuracy:.2f}% < 95%")

        if passed_pages == total_pages:
            log["Result"] = True
            log["comments"] = f"✅ 所有 {total_pages} 页均通过准确率>=95% 的检测"
        else:
            log["comments"] = f"❌ {total_pages - passed_pages} 页未达到准确率要求：\n" + "\n".join(page_logs)

    except Exception as e:
        log["Process"] = False
        log["comments"] += f"[异常错误] {str(e)}"

    print(log["comments"])
    write_result(result_path, log)


def write_result(result_path, log):
    os.makedirs(os.path.dirname(result_path) or '.', exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False, default=str) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="拆分后页面文件夹路径")
    parser.add_argument("--groundtruth", type=str, required=True, help="标准答案页面文件夹路径")
    parser.add_argument("--result", type=str, required=True, help="结果写入的 JSONL 路径")
    args = parser.parse_args()

    evaluate(args.output, args.groundtruth, args.result)
