import argparse
import csv
import json
import os
import re
from datetime import datetime
from collections import defaultdict

def load_txt_file(file_path):
    """加载TXT文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content, None
    except Exception as e:
        return "", str(e)

def extract_file_blocks(content):
    """从TXT内容中提取文件名和对应的表格数据块"""
    file_blocks = {}
    current_file = None
    current_block = []
    
    # 尝试使用文件名标记分割内容
    lines = content.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 检测文件名行 - 支持多种可能的格式
        file_name_match = None
        if line.startswith("文件名:") or line.startswith("File name:"):
            file_name_match = re.search(r'(?:文件名|File name):?\s*(.+?)(?:\s|$)', line)
        elif "文件名" in line:
            file_name_match = re.search(r'.*文件名:?\s*(.+?)(?:\s|$)', line)
        elif re.match(r'^[^:]*\.xlsx?\s*$', line):  # 直接是文件名.xls(x)的情况
            file_name_match = re.match(r'^([^:]*\.xlsx?)$', line)
        
        if file_name_match:
            # 如果已经有当前文件，保存它的数据块
            if current_file and current_block:
                file_blocks[current_file] = '\n'.join(current_block)
            
            # 提取新的文件名
            current_file = file_name_match.group(1).strip()
            current_block = []
        elif current_file is not None:
            # 添加到当前块
            current_block.append(line)
        
        i += 1
    
    # 处理最后一个文件块
    if current_file and current_block:
        file_blocks[current_file] = '\n'.join(current_block)
    
    return file_blocks

def parse_table_content(block_content):
    """解析表格块内容，提取数据结构"""
    sheets_data = []
    current_sheet = []
    
    lines = block_content.split('\n')
    i = 0
    in_sheet = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            i += 1
            continue
        
        # 检测Sheet标记
        sheet_match = re.search(r'Sheet:?', line)
        if sheet_match:
            # 如果找到新的Sheet，保存之前的sheet数据
            if in_sheet and current_sheet:
                sheets_data.append(current_sheet)
                current_sheet = []
            
            in_sheet = True
            i += 1
            continue
        
        # 处理数据行
        if in_sheet or not sheets_data:  # 如果没有明确的Sheet标记，也尝试解析
            # 清理行号
            cleaned_line = re.sub(r'^\d+\s+', '', line)
            
            # 分割单元格数据
            # 首先尝试制表符或多个空格分割
            cells = re.split(r'\s{2,}|\t', cleaned_line)
            
            # 如果分割后只有一个元素，尝试使用单个空格分割
            if len(cells) <= 1:
                cells = re.split(r'\s+', cleaned_line)
            
            if cells:
                current_sheet.append(cells)
        
        i += 1
    
    # 保存最后一个sheet
    if current_sheet:
        sheets_data.append(current_sheet)
    
    # 如果没有明确的sheet分隔，但有数据，则作为单个sheet处理
    if not sheets_data and lines:
        # 重新解析为单个sheet
        current_sheet = []
        for line in lines:
            if line.strip():
                # 清理行号
                cleaned_line = re.sub(r'^\d+\s+', '', line)
                # 分割单元格
                cells = re.split(r'\s{2,}|\t', cleaned_line)
                if len(cells) <= 1:
                    cells = re.split(r'\s+', cleaned_line)
                if cells:
                    current_sheet.append(cells)
        
        if current_sheet:
            sheets_data.append(current_sheet)
    
    return sheets_data

def normalize_value(value):
    """标准化单元格值，处理各种格式差异"""
    # 转换为字符串并去除前后空格
    value_str = str(value).strip()
    
    # 标准化日期格式
    date_match = re.match(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})(?:\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)?', value_str)
    if date_match:
        # 提取日期部分
        date_part = date_match.group(1)
        # 统一分隔符为-
        date_part = date_part.replace('/', '-')
        # 确保日期格式为yyyy-mm-dd
        date_parts = date_part.split('-')
        if len(date_parts) == 3:
            year = date_parts[0]
            month = date_parts[1].zfill(2)
            day = date_parts[2].zfill(2)
            value_str = f"{year}-{month}-{day}"
    
    # 统一数字格式
    number_match = re.match(r'^[-+]?\d+(?:\.\d+)?$', value_str)
    if number_match:
        try:
            # 尝试转换为浮点数，然后去除尾随零
            num_value = float(value_str)
            # 如果是整数，移除小数点
            if num_value.is_integer():
                value_str = str(int(num_value))
            else:
                value_str = str(num_value).rstrip('0').rstrip('.')
        except:
            pass
    
    return value_str

def calculate_sheet_similarity(pred_sheet, truth_sheet):
    """计算两个工作表的内容相似度"""
    # 标准化所有单元格值
    pred_values = set()
    truth_values = set()
    
    # 处理预测数据
    for row in pred_sheet:
        for cell in row:
            normalized = normalize_value(cell)
            if normalized:  # 忽略空单元格
                pred_values.add(normalized)
    
    # 处理真实数据
    for row in truth_sheet:
        for cell in row:
            normalized = normalize_value(cell)
            if normalized:  # 忽略空单元格
                truth_values.add(normalized)
    
    # 计算交集和并集
    intersection = pred_values.intersection(truth_values)
    union = pred_values.union(truth_values)
    
    # Jaccard相似度
    if not union:
        return 0.0
    
    similarity = len(intersection) / len(union) * 100
    return similarity

def evaluate_file_similarity(pred_sheets, truth_sheets):
    """评估文件相似度"""
    if not pred_sheets or not truth_sheets:
        return 0.0
    
    # 计算每个sheet的相似度
    total_similarity = 0.0
    sheet_count = min(len(pred_sheets), len(truth_sheets))
    
    for i in range(sheet_count):
        sheet_similarity = calculate_sheet_similarity(
            pred_sheets[i], 
            truth_sheets[i]
        )
        total_similarity += sheet_similarity
    
    # 平均相似度
    avg_similarity = total_similarity / sheet_count if sheet_count > 0 else 0.0
    
    # 如果sheet数量不同，减少相似度
    sheet_diff_penalty = abs(len(pred_sheets) - len(truth_sheets)) * 5  # 每个多余或缺少的sheet减少5%
    final_similarity = max(0, avg_similarity - sheet_diff_penalty)
    
    return final_similarity

def evaluate(pred_file, truth_file):
    """评估函数"""
    pred_content, pred_err = load_txt_file(pred_file)
    truth_content, truth_err = load_txt_file(truth_file)
    
    process_ok = True
    comments = []
    
    # 读取错误检查
    if pred_err:
        comments.append(f"[预测文件读取失败] {pred_err}")
        process_ok = False
    if truth_err:
        comments.append(f"[GT文件读取失败] {truth_err}")
        process_ok = False
    if not process_ok:
        return {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }
    
    # 提取文件块
    pred_file_blocks = extract_file_blocks(pred_content)
    truth_file_blocks = extract_file_blocks(truth_content)
    
    # 文件名比较
    pred_files = set(pred_file_blocks.keys())
    truth_files = set(truth_file_blocks.keys())
    
    comments.append(f"预测文件包含 {len(pred_files)} 个Excel文件数据块")
    comments.append(f"GT文件包含 {len(truth_files)} 个Excel文件数据块")
    
    if len(pred_files) == 0:
        comments.append("⚠️ 预测文件中未找到任何Excel文件数据块！")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }
    
    if len(truth_files) == 0:
        comments.append("⚠️ GT文件中未找到任何Excel文件数据块！")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }
    
    # 计算文件匹配情况
    common_files = pred_files.intersection(truth_files)
    missing_files = truth_files - pred_files
    extra_files = pred_files - truth_files
    
    # 文件名匹配率
    file_match_rate = len(common_files) / len(truth_files) * 100 if truth_files else 0
    comments.append(f"文件名匹配率: {file_match_rate:.2f}%")
    
    if missing_files:
        comments.append(f"缺少的文件: {', '.join(missing_files)}")
    if extra_files:
        comments.append(f"多余的文件: {', '.join(extra_files)}")
    
    # 内容相似度评分
    total_similarity = 0.0
    file_count = 0
    
    # 处理完全匹配的文件名
    for file_name in common_files:
        pred_content_block = pred_file_blocks[file_name]
        truth_content_block = truth_file_blocks[file_name]
        
        # 解析表格内容
        pred_sheets = parse_table_content(pred_content_block)
        truth_sheets = parse_table_content(truth_content_block)
        
        # 计算文件相似度
        file_similarity = evaluate_file_similarity(pred_sheets, truth_sheets)
        
        comments.append(f"文件 '{file_name}' 内容相似度: {file_similarity:.2f}%")
        total_similarity += file_similarity
        file_count += 1
    
    # 处理可能因文件名略有不同而未匹配的文件
    # 通过内容相似度尝试匹配
    if missing_files and extra_files:
        for missing_file in list(missing_files):
            best_match = None
            best_similarity = 0
            
            truth_content_block = truth_file_blocks[missing_file]
            truth_sheets = parse_table_content(truth_content_block)
            
            for extra_file in list(extra_files):
                pred_content_block = pred_file_blocks[extra_file]
                pred_sheets = parse_table_content(pred_content_block)
                
                similarity = evaluate_file_similarity(pred_sheets, truth_sheets)
                if similarity > best_similarity and similarity > 60:  # 要求至少60%相似
                    best_similarity = similarity
                    best_match = extra_file
            
            if best_match:
                comments.append(f"文件名不同但内容相似: '{missing_file}' 与 '{best_match}', 相似度: {best_similarity:.2f}%")
                total_similarity += best_similarity
                file_count += 1
                missing_files.remove(missing_file)
                extra_files.remove(best_match)
    
    # 计算平均文件相似度
    avg_similarity = total_similarity / len(truth_files) if truth_files else 0
    
    # 因缺少文件而降低评分
    if missing_files:
        missing_penalty = len(missing_files) / len(truth_files) * 100
        comments.append(f"因缺少文件降低评分: -{missing_penalty:.2f}%")
        avg_similarity = max(0, avg_similarity - missing_penalty)
    
    comments.append(f"所有文件平均内容相似度: {avg_similarity:.2f}%")
    
    # 文件匹配权重和内容相似度权重
    file_match_weight = 0.3
    content_similarity_weight = 0.7
    
    # 最终得分
    final_score = (file_match_rate * file_match_weight + avg_similarity * content_similarity_weight)
    passed = final_score >= 75
    
    comments.append(f"最终评分 (文件匹配{file_match_weight*100}% + 内容相似度{content_similarity_weight*100}%): {final_score:.2f}% (阈值=75%)")
    
    if passed:
        comments.append("✅ 测试通过！")
    else:
        comments.append("❌ 测试未通过！")
    
    # 如果结构化解析失败，尝试基础内容比较
    if file_count == 0:
        comments.append("注意: 结构化解析未找到匹配，尝试基础内容比较")
        
        # 计算整体内容的词汇重叠度
        pred_words = set(re.findall(r'\b\w+\b', pred_content.lower()))
        truth_words = set(re.findall(r'\b\w+\b', truth_content.lower()))
        
        common_words = pred_words.intersection(truth_words)
        all_words = pred_words.union(truth_words)
        
        if all_words:
            word_overlap = len(common_words) / len(all_words) * 100
            comments.append(f"内容词汇重叠度: {word_overlap:.2f}%")
            
            # 如果词汇重叠度高，也可以通过
            if word_overlap >= 75:
                comments.append("基于词汇重叠度: ✅ 测试通过！")
                return {
                    "Process": True,
                    "Result": True,
                    "TimePoint": datetime.now().isoformat(),
                    "comments": "\n".join(comments)
                }
    
    return {
        "Process": True,
        "Result": passed,
        "TimePoint": datetime.now().isoformat(),
        "comments": "\n".join(comments)
    }

def append_result_to_jsonl(result_path, result_dict):
    os.makedirs(os.path.dirname(result_path) or '.', exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, default=str)
        f.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="提取出的整体表格路径")
    parser.add_argument("--groundtruth", type=str, required=True, help="标准整体表格路径")
    parser.add_argument("--result", type=str, required=True, help="结果输出 JSONL 文件路径")
    args = parser.parse_args()
    
    result_dict = evaluate(args.output, args.groundtruth)
    append_result_to_jsonl(args.result, result_dict)
    print("[评估完成] 结果摘要：")
    print(json.dumps(result_dict, ensure_ascii=False, indent=2, default=str))