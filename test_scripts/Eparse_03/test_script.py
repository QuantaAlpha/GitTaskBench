import argparse
import json
import os
import datetime
import re
from collections import defaultdict

def normalize_value(value):
    """标准化值，处理数字和字符串的一致性"""
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()

def extract_cell_data(json_data):
    """从不同的JSON结构中提取单元格数据，返回标准化的单元格集合"""
    cells = []
    
    # 处理GT格式
    if isinstance(json_data, dict) and "sheets" in json_data:
        for sheet_name, sheet_data in json_data["sheets"].items():
            for row in sheet_data.get("rows", []):
                row_index = row.get("row_index", 0)
                for cell in row.get("cells", []):
                    cells.append({
                        "row": row_index,
                        "column": cell.get("column_index"),
                        "value": normalize_value(cell.get("value")),
                        "excel_RC": cell.get("excel_RC"),
                        "c_header": cell.get("c_header"),
                        "r_header": cell.get("r_header"),
                        "type": cell.get("type")
                    })
    
    # 处理Agent输出格式
    elif isinstance(json_data, list):
        for table in json_data:
            for cell in table.get("data", []):
                cells.append({
                    "row": cell.get("row"),
                    "column": cell.get("column"),
                    "value": normalize_value(cell.get("value")),
                    "excel_RC": cell.get("excel_RC"),
                    "c_header": cell.get("c_header"),
                    "r_header": cell.get("r_header"),
                    "type": cell.get("type")
                })
    
    # 处理其他可能的格式
    else:
        try:
            # 尝试递归查找所有类似单元格的数据结构
            def find_cells(obj, path=""):
                if isinstance(obj, dict):
                    # 检查是否是单元格结构
                    if all(k in obj for k in ["row", "column", "value"]) or \
                       all(k in obj for k in ["row_index", "column_index", "value"]):
                        row = obj.get("row", obj.get("row_index", 0))
                        column = obj.get("column", obj.get("column_index", 0))
                        cells.append({
                            "row": row,
                            "column": column,
                            "value": normalize_value(obj.get("value")),
                            "excel_RC": obj.get("excel_RC", f"{chr(65+column)}{row+1}"),
                            "c_header": obj.get("c_header", str(column+1)),
                            "r_header": obj.get("r_header", str(row+1)),
                            "type": obj.get("type", "")
                        })
                    else:
                        for k, v in obj.items():
                            find_cells(v, f"{path}.{k}" if path else k)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_cells(item, f"{path}[{i}]")
            
            find_cells(json_data)
        except Exception as e:
            print(f"无法解析JSON结构: {str(e)}")
    
    return cells

def compute_cell_similarity(cells1, cells2):
    """计算两个单元格集合的相似度"""
    if not cells1 and not cells2:
        return 1.0  # 两者都为空，视为完全匹配
    
    if not cells1 or not cells2:
        return 0.0  # 一方为空，另一方不为空
    
    # 创建位置到单元格的映射
    cells1_dict = {(cell["row"], cell["column"]): cell for cell in cells1}
    cells2_dict = {(cell["row"], cell["column"]): cell for cell in cells2}
    
    # 获取所有唯一的单元格位置
    all_positions = set(cells1_dict.keys()) | set(cells2_dict.keys())
    
    # 计算匹配的单元格数量
    matches = 0
    total_weight = 0
    
    for pos in all_positions:
        weight = 1  # 单元格权重
        total_weight += weight
        
        if pos in cells1_dict and pos in cells2_dict:
            cell1 = cells1_dict[pos]
            cell2 = cells2_dict[pos]
            
            # 比较值
            if normalize_value(cell1["value"]) == normalize_value(cell2["value"]):
                matches += 0.6 * weight  # 值匹配占60%权重
            
            # 比较其他元数据 (各占10%权重)
            for key in ["excel_RC", "c_header", "r_header", "type"]:
                if key in cell1 and key in cell2 and normalize_value(cell1[key]) == normalize_value(cell2[key]):
                    matches += 0.1 * weight
    
    similarity = matches / total_weight if total_weight > 0 else 0
    return similarity

def is_valid_file(file_path):
    """判断文件是否存在且非空"""
    return os.path.isfile(file_path) and os.path.getsize(file_path) > 0

def evaluate(pred_file, gt_file):
    """读取文件并计算相似度"""
    try:
        with open(pred_file, 'r', encoding='utf-8') as f_pred:
            pred_text = f_pred.read()
        with open(gt_file, 'r', encoding='utf-8') as f_gt:
            gt_text = f_gt.read()
    except Exception as e:
        return None, f"❌ 文件读取错误: {str(e)}"
    
    try:
        # 解析JSON
        pred_json = json.loads(pred_text)
        gt_json = json.loads(gt_text)
        
        # 提取单元格数据
        pred_cells = extract_cell_data(pred_json)
        gt_cells = extract_cell_data(gt_json)
        
        # 计算单元格内容相似度
        similarity = compute_cell_similarity(pred_cells, gt_cells)
        
        return similarity, f"✅ 相似度计算完成: {similarity:.4f} (共 {len(gt_cells)} 个GT单元格, {len(pred_cells)} 个预测单元格)"
    except json.JSONDecodeError:
        # 如果JSON解析失败，回退到原始的Levenshtein相似度计算
        try:
            import Levenshtein
            levenshtein_distance = Levenshtein.distance(pred_text, gt_text)
            similarity = 1 - levenshtein_distance / max(len(pred_text), len(gt_text))
            return similarity, f"⚠️ JSON解析失败，使用Levenshtein相似度: {similarity:.4f}"
        except ImportError:
            return 0.0, "❌ JSON解析失败且Levenshtein库不可用"
    except Exception as e:
        return 0.0, f"❌ 评估过程出错: {str(e)}"

def save_result(result_path, data):
    """保存结果到jsonl文件"""
    os.makedirs(os.path.dirname(result_path) or '.', exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Compare similarity between predicted and ground truth Excel JSON data.")
    parser.add_argument('--output', required=True, help="Path to predicted JSON file.")
    parser.add_argument('--groundtruth', required=True, help="Path to ground truth JSON file.")
    parser.add_argument('--result', required=True, help="Path to save evaluation results (.jsonl).")
    args = parser.parse_args()
    
    result_dict = {
        "Process": False,
        "Result": False,
        "TimePoint": datetime.datetime.now().isoformat(),
        "comments": ""
    }
    
    # Step 1: 检查文件是否存在且非空
    if not is_valid_file(args.output):
        result_dict["comments"] = "❌ 预测文件不存在或为空"
        save_result(args.result, result_dict)
        print(result_dict["comments"])
        return
    
    if not is_valid_file(args.groundtruth):
        result_dict["comments"] = "❌ GT文件不存在或为空"
        save_result(args.result, result_dict)
        print(result_dict["comments"])
        return
    
    result_dict["Process"] = True
    
    # Step 2: 评估相似度
    similarity, msg = evaluate(args.output, args.groundtruth)
    if similarity is None:
        result_dict["comments"] = msg
        save_result(args.result, result_dict)
        print(msg)
        return
    
    result_dict["comments"] = msg
    result_dict["Result"] = similarity >= 0.8
    save_result(args.result, result_dict)
    
    print(msg)
    if result_dict["Result"]:
        print("✅ Passed: 相似度大于等于 0.8")
    else:
        print("❌ Failed: 相似度低于 0.8")

if __name__ == "__main__":
    main()