import argparse
import json
import os
import re
from datetime import datetime
from ast import literal_eval
import traceback

def normalize_json_item(item):
    """
    将JSON对象标准化处理，去除格式差异
    """
    if isinstance(item, str):
        # 尝试解析字符串为字典
        try:
            item = json.loads(item)
        except:
            try:
                # 尝试用ast.literal_eval解析不标准的JSON格式
                item = literal_eval(item)
            except:
                # 如果解析失败，则返回原字符串
                return item
    
    # 确保所有键都是字符串
    result = {}
    for k, v in item.items():
        # 转换键为字符串并去除空白
        key = str(k).strip().lower()
        # 对值进行处理
        if isinstance(v, str):
            # 字符串值去除多余空白并转为小写（除了type字段）
            if key == 'type':
                value = v.strip()  # type字段保留大小写
            else:
                value = v.strip().lower()
        else:
            value = v
        result[key] = value
    
    return result

def parse_gt_format(content):
    """
    专门处理gt.txt格式的解析器
    这种格式的特点是多行字典，每个字典由多行组成，字典之间用逗号分隔
    """
    items = []
    # 替换掉所有的换行，将内容变成一行
    content = content.replace('\n', ' ')
    
    # 尝试解析为列表
    try:
        # 如果整个内容被方括号包围，去掉方括号
        if content.strip().startswith('[') and content.strip().endswith(']'):
            content = content.strip()[1:-1]
        
        # 分割多个字典（每个字典以 { 开始，以 }, 或 } 结束）
        dict_pattern = r'\{[^{}]*\}'
        dict_matches = re.findall(dict_pattern, content)
        
        for dict_str in dict_matches:
            try:
                item = literal_eval(dict_str)
                items.append(normalize_json_item(item))
            except Exception as e:
                print(f"解析字典失败: {dict_str[:50]}... 错误: {e}")
    except Exception as e:
        print(f"解析gt格式失败: {e}")
    
    print(f"从gt格式解析出 {len(items)} 个项目")
    return items

def parse_json_line_format(content):
    """
    解析每行一个JSON对象的格式
    """
    items = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            # 尝试解析为JSON对象
            item = json.loads(line)
            items.append(normalize_json_item(item))
        except:
            try:
                # 尝试用ast.literal_eval解析不标准的JSON格式
                item = literal_eval(line)
                items.append(normalize_json_item(item))
            except Exception as e:
                print(f"无法解析行: {line[:50]}... 错误: {e}")
    
    print(f"从JSON行格式解析出 {len(items)} 个项目")
    return items

def load_json_items(file_path):
    """
    读取包含JSON对象的文件，返回标准化的对象列表
    支持多种格式：每行一个JSON、单个大JSON数组、字典列表格式、多行字典格式
    """
    print(f"正在解析文件: {file_path}")
    items = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
            # 检查文件格式
            if not content:
                print("文件为空")
                return items
                
            # 1. 首先尝试gt.txt特定格式
            if "{'c_header':" in content or '{"c_header":' in content or "'c_header':" in content:
                print("检测到gt.txt格式，使用专用解析器")
                items = parse_gt_format(content)
                if items:
                    return items
            
            # 2. 尝试解析为JSON数组
            if content.startswith('[') and content.endswith(']'):
                try:
                    array_items = json.loads(content)
                    for item in array_items:
                        items.append(normalize_json_item(item))
                    print(f"从JSON数组解析出 {len(items)} 个项目")
                    return items
                except Exception as e:
                    print(f"JSON数组解析失败: {e}")
                    
                    # 尝试Python列表字面量
                    try:
                        array_items = literal_eval(content)
                        for item in array_items:
                            items.append(normalize_json_item(item))
                        print(f"从Python列表解析出 {len(items)} 个项目")
                        return items
                    except Exception as e:
                        print(f"Python列表解析失败: {e}")
            
            # 3. 尝试按行解析JSON对象
            items = parse_json_line_format(content)
            if items:
                return items
            
            # 4. 最后尝试提取所有可能的字典
            print("尝试提取所有可能的字典...")
            dict_pattern = r'\{[^{}]*\}'
            dicts = re.findall(dict_pattern, content)
            for d in dicts:
                try:
                    item = literal_eval(d)
                    items.append(normalize_json_item(item))
                except Exception as e:
                    print(f"字典提取失败: {d[:30]}... 错误: {e}")
            
            if items:
                print(f"从字典提取中解析出 {len(items)} 个项目")
                return items
                
    except Exception as e:
        print(f"读取文件时出错: {e}")
        traceback.print_exc()
    
    return items

def compare_items(pred_items, gt_items):
    """
    比较预测项和真实项，计算关键字段的匹配度
    """
    if not pred_items or not gt_items:
        return 0, "没有有效的项目可比较"
    
    print(f"比较 {len(pred_items)} 个预测项与 {len(gt_items)} 个真实项")
    
    # 关键字段列表，这些是我们认为更重要的字段
    key_fields = ['value', 'row', 'column', 'excel_rc', 'c_header', 'r_header', 'sheet', 'f_name']
    
    total_matches = 0
    total_fields = 0
    missing_items = 0
    
    # 匹配项目数量（以较少的一方为准）
    expected_matches = min(len(pred_items), len(gt_items))
    
    # 如果预测项少于真实项，记录缺失数量
    if len(pred_items) < len(gt_items):
        missing_items = len(gt_items) - len(pred_items)
    
    # 打印部分数据示例以便调试
    print("预测项样例:")
    for i, item in enumerate(pred_items[:2]):
        print(f"  项目 {i}: {item}")
    
    print("真实项样例:")
    for i, item in enumerate(gt_items[:2]):
        print(f"  项目 {i}: {item}")
    
    # 逐项比较
    for i in range(min(len(pred_items), len(gt_items))):
        pred_item = pred_items[i]
        gt_item = gt_items[i]
        
        item_matches = 0
        item_fields = 0
        
        # 比较关键字段
        for field in key_fields:
            # 对于预测项，尝试兼容不同的大小写形式
            pred_fields = [f.lower() for f in pred_item.keys()]
            pred_field_key = None
            
            # 查找匹配的字段（忽略大小写）
            if field in pred_item:
                pred_field_key = field
            else:
                for k in pred_item.keys():
                    if k.lower() == field.lower():
                        pred_field_key = k
                        break
            
            # 对于真实项，也尝试兼容不同的大小写形式
            gt_field_key = None
            if field in gt_item:
                gt_field_key = field
            else:
                for k in gt_item.keys():
                    if k.lower() == field.lower():
                        gt_field_key = k
                        break
            
            # 如果两者都存在该字段，进行比较
            if pred_field_key is not None and gt_field_key is not None:
                item_fields += 1
                pred_value = pred_item[pred_field_key]
                gt_value = gt_item[gt_field_key]
                
                # 对excel_rc字段忽略大小写
                if field.lower() == 'excel_rc':
                    if str(pred_value).upper() == str(gt_value).upper():
                        item_matches += 1
                # 对数值型字段进行数值比较
                elif field.lower() in ['row', 'column'] and isinstance(pred_value, (int, float)) and isinstance(gt_value, (int, float)):
                    if pred_value == gt_value:
                        item_matches += 1
                # type字段特殊处理
                elif field.lower() == 'type':
                    # 提取类型名称，忽略引号和class部分
                    pred_type = re.sub(r"[<>'\"]|class\s+", "", str(pred_value)).strip()
                    gt_type = re.sub(r"[<>'\"]|class\s+", "", str(gt_value)).strip()
                    if pred_type == gt_type:
                        item_matches += 1
                # 其他字段进行标准化比较
                elif str(pred_value).lower() == str(gt_value).lower():
                    item_matches += 1
        
        # 计入总匹配
        if item_fields > 0:
            total_matches += item_matches
            total_fields += item_fields
    
    # 计算匹配率
    if total_fields == 0:
        accuracy = 0
        details = "未找到有效的字段进行比较"
    else:
        accuracy = total_matches / total_fields
        details = f"匹配字段: {total_matches}/{total_fields}"
        
        # 如果有缺失项目，降低分数
        if missing_items > 0:
            penalty = min(0.2, missing_items / len(gt_items) * 0.5)  # 最多扣20%
            accuracy = max(0, accuracy - penalty)
            details += f", 缺失项目数: {missing_items}, 应用了 {penalty:.2f} 的惩罚"
    
    return accuracy, details

def evaluate(pred_path, gt_path):
    """按解析后的内容评估"""
    threshold = 0.70  # 固定阈值
    
    # 加载和标准化数据
    pred_items = load_json_items(pred_path)
    gt_items = load_json_items(gt_path)
    
    # 结果字典初始化
    result = {
        "Process": True,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }
    
    # 检查输入文件是否有效
    if not pred_items:
        result["Process"] = False
        result["comments"] = "预测文件解析为空，无法进行评估！"
        return result
    
    if not gt_items:
        result["Process"] = False
        result["comments"] = "❌ ground truth解析为空！"
        result["Result"] = False
        return result
    
    # 比较项目并计算匹配率
    accuracy, details = compare_items(pred_items, gt_items)
    
    # 根据准确率判断结果
    if accuracy >= threshold:
        result["Result"] = True
        result["comments"] = f"✅ 测试通过！内容匹配率={accuracy:.4f} ≥ {threshold}。{details}"
    else:
        result["Result"] = False
        result["comments"] = f"❌ 测试未通过。内容匹配率={accuracy:.4f} < {threshold}。{details}"
    
    print(result["comments"])
    return result

def save_result(result, result_file):
    """保存结果到 jsonl 文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(result_file) or '.', exist_ok=True)
    
    # 追加模式写入，确保每条记录单独一行
    with open(result_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Evaluate Excel cell parsing output by content similarity and save results")
    parser.add_argument("--output", required=True, help="Predicted output file path")
    parser.add_argument("--groundtruth", required=True, help="Ground truth file path")
    parser.add_argument("--result", required=True, help="Result output file path (JSONL format)")
    args = parser.parse_args()
    
    # 获取评估结果
    result = evaluate(args.output, args.groundtruth)
    
    # 将结果保存到指定的 jsonl 文件
    save_result(result, args.result)
    print(f"结果已保存到 {args.result}")

if __name__ == "__main__":
    main()