import argparse
import os
import xml.etree.ElementTree as ET
import csv
import json
import re
from datetime import datetime

def check_file_valid(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ 文件为空: {file_path}")
        return False
    return True

def clean_text(text):
    """Clean and normalize text for comparison"""
    if text is None:
        return ""
    # Remove quotes at beginning and end (different agents might handle quotes differently)
    text = text.strip()
    text = re.sub(r'^[""]|[""]$', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_xml_content(file_path):
    """提取XML文件中的内容，过滤掉可能的注释和其他非XML内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 如果找到XML声明就保留，否则添加一个
        xml_decl_match = re.search(r'<\?xml[^>]+\?>', content)
        if xml_decl_match:
            xml_decl = xml_decl_match.group(0)
            content = content[xml_decl_match.end():]
        else:
            xml_decl = '<?xml version="1.0" encoding="UTF-8"?>'
            
        # 移除XML注释
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # 移除不合法的XML字符
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        # 查找第一个<和最后一个>之间的内容(取出可能的非XML前缀和后缀)
        start_idx = content.find('<')
        end_idx = content.rfind('>')
        if start_idx >= 0 and end_idx > start_idx:
            content = content[start_idx:end_idx+1]
            
        # 确保有一个根元素
        if not re.search(r'<\w+[^>]*>.*</\w+>', content, re.DOTALL):
            content = f"<root>{content}</root>"
            
        return xml_decl + content
    except Exception as e:
        print(f"❌ 读取XML文件失败: {e}")
        return None

def parse_xml(file_path):
    """通用XML解析函数，识别各种可能的结构"""
    try:
        xml_content = extract_xml_content(file_path)
        if not xml_content:
            return []
            
        # 尝试解析XML
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"❌ XML 解析错误，尝试修复: {e}")
        try:
            # 尝试处理不完整的XML
            xml_content = re.sub(r'<\?xml[^>]+\?>', '', xml_content)
            xml_content = f"<root>{xml_content}</root>"
            root = ET.fromstring(xml_content)
        except ET.ParseError as e2:
            print(f"❌ XML 修复失败: {e2}")
            # 最后尝试一种更激进的修复方法
            try:
                pattern = r'<(.*?)>(.*?)</(.*?)>'
                matches = re.findall(pattern, xml_content, re.DOTALL)
                items_xml = ''.join([f'<item>{m[1]}</item>' for m in matches if len(m) >= 2])
                root = ET.fromstring(f"<root>{items_xml}</root>")
            except:
                print("❌ 所有XML修复尝试均失败")
                return []

    records = []
    
    # 获取所有可能的项目元素
    # 常见的标签模式: quote, item, entry, record 等
    item_tags = ['quote', 'item', 'entry', 'record', 'row', 'data']
    
    # 尝试找出根元素下的直接子元素，如果数量合理，可能这些就是我们要找的项目
    direct_children = list(root)
    
    # 如果直接子元素数量较多(>1)且结构类似，它们可能就是项目元素
    candidates = []
    if len(direct_children) > 1:
        # 检查这些元素是否具有相似的结构
        first_child_tags = set([child.tag for child in direct_children[0]] if len(direct_children) > 0 else [])
        if all(set([child.tag for child in elem]) == first_child_tags for elem in direct_children[1:]):
            candidates.extend(direct_children)
    
    # 如果没有找到合适的直接子元素，尝试预定义的项目标签
    if not candidates:
        for tag in item_tags:
            items = root.findall(f".//{tag}")
            if items:
                candidates.extend(items)
                break
    
    # 如果仍然没有找到，尝试查找任何包含author和text子元素的元素
    if not candidates:
        for elem in root.findall(".//*"):
            has_author = any(child.tag == 'author' or 'author' in child.tag.lower() for child in elem)
            has_text = any(child.tag == 'text' or 'text' in child.tag.lower() for child in elem)
            if has_author and has_text:
                candidates.append(elem)
    
    # 从候选项目中提取author和text信息
    for item in candidates:
        author_content = ""
        text_content = ""
        
        # 方法1: 直接查找特定标签
        for child in item:
            if child.tag.lower() == 'author' or 'author' in child.tag.lower():
                author_content = clean_text(child.text)
            elif child.tag.lower() == 'text' or 'text' in child.tag.lower() or child.tag.lower() == 'quote':
                text_content = clean_text(child.text)
        
        # 方法2: 查找包含特定关键词的任何元素
        if not author_content or not text_content:
            for elem in item.findall(".//*"):
                if (elem.tag.lower() == 'author' or 'author' in elem.tag.lower()) and not author_content:
                    author_content = clean_text(elem.text)
                elif (elem.tag.lower() == 'text' or 'text' in elem.tag.lower() or 'quote' in elem.tag.lower() or 'content' in elem.tag.lower()) and not text_content:
                    text_content = clean_text(elem.text)
        
        # 方法3: 从属性中查找
        for attr_name, attr_value in item.attrib.items():
            if ('author' in attr_name.lower()) and not author_content:
                author_content = clean_text(attr_value)
            elif ('text' in attr_name.lower() or 'quote' in attr_name.lower() or 'content' in attr_name.lower()) and not text_content:
                text_content = clean_text(attr_value)
        
        # 方法4: 如果项目自身只有纯文本且包含特定模式，尝试提取
        if (not author_content or not text_content) and item.text and item.text.strip():
            # 尝试匹配作者-引言模式，如 "Author Name: 'Quote text'"
            author_quote_match = re.search(r'([^:]+):\s*[\'"](.+?)[\'"]', item.text.strip())
            if author_quote_match:
                if not author_content:
                    author_content = clean_text(author_quote_match.group(1))
                if not text_content:
                    text_content = clean_text(author_quote_match.group(2))
        
        # 只收录有内容的记录
        if author_content and text_content:
            records.append({
                "author": author_content,
                "text": text_content
            })
    
    # 如果以上方法都找不到记录，尝试直接从文本中提取
    if not records:
        print("⚠️ 常规解析方法未找到记录，尝试直接文本提取...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试匹配作者和引言模式
            pattern = r'<(author|text)>(.*?)</(author|text)>'
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            
            authors = [clean_text(m[1]) for m in matches if m[0].lower() == 'author' and m[2].lower() == 'author']
            texts = [clean_text(m[1]) for m in matches if m[0].lower() == 'text' and m[2].lower() == 'text']
            
            # 如果找到相等数量的author和text，假设它们是成对的
            if len(authors) == len(texts) and len(authors) > 0:
                records = [{"author": a, "text": t} for a, t in zip(authors, texts)]
        except Exception as e:
            print(f"❌ 文本提取失败: {e}")
    
    return records

def parse_csv(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = []
            for row in reader:
                if "text" in row and "author" in row:
                    records.append({
                        "text": clean_text(row["text"]),
                        "author": clean_text(row["author"])
                    })
            return records
    except Exception as e:
        print(f"❌ CSV 读取失败: {e}")
        return []

def find_best_matches(preds, gts):
    """找到预测和真实值之间的最佳匹配"""
    matched_pairs = []
    remaining_preds = list(range(len(preds)))
    
    for i, gt_item in enumerate(gts):
        best_score = -1
        best_idx = -1
        
        for j in remaining_preds:
            pred_item = preds[j]
            score = 0
            
            # 基于文本相似度的评分
            for field in ["author", "text"]:
                gt_val = gt_item.get(field, "").lower()
                pred_val = pred_item.get(field, "").lower()
                
                # 完全匹配
                if gt_val == pred_val:
                    score += 2
                # 部分匹配 (一个包含另一个)
                elif gt_val in pred_val or pred_val in gt_val:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_idx = j
        
        if best_idx >= 0:
            matched_pairs.append((i, best_idx))
            remaining_preds.remove(best_idx)
        else:
            # 如果没有找到匹配，使用默认的索引匹配
            default_idx = i if i < len(preds) else 0
            matched_pairs.append((i, default_idx))
    
    return matched_pairs

def evaluate_scraping_xml(pred_file, gt_file, threshold=0.95, result_file=None):
    if not check_file_valid(pred_file) or not check_file_valid(gt_file):
        return {}, False
    
    preds = parse_xml(pred_file)
    gts = parse_csv(gt_file)
    
    if not preds:
        print("❌ 无法从XML中提取有效的records")
        if result_file:
            result = {
                "Process": True,
                "Results": False,
                "TimePoint": datetime.now().isoformat(),
                "comments": "XML解析失败，无法提取有效记录"
            }
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
        return {}, False
    
    print(f"✓ 从XML中提取了 {len(preds)} 条记录")
    for i, record in enumerate(preds[:3]):  # 只显示前3条作为示例
        print(f"  记录 {i+1}: 作者='{record['author']}', 文本='{record['text'][:30]}...'")
    if len(preds) > 3:
        print(f"  ... 以及另外 {len(preds)-3} 条记录")
    
    if len(preds) != len(gts):
        print(f"⚠️ 预测结果与标注数据长度不一致（预测 {len(preds)} 条，真实 {len(gts)} 条），寻找最佳匹配。")
    
    num_samples = min(len(preds), len(gts))
    if num_samples == 0:
        print("❌ 错误：无可比对的数据。")
        return {}, False
    
    fields = ["author", "text"]
    correct_counts = {field: 0 for field in fields}
    
    # 寻找预测和真实值之间的最佳匹配
    matched_pairs = find_best_matches(preds, gts[:num_samples])
    
    for gt_idx, pred_idx in matched_pairs:
        for field in fields:
            gt_val = clean_text(gts[gt_idx].get(field, "")).lower()
            pred_val = clean_text(preds[pred_idx].get(field, "")).lower()
            
            # 完全匹配或几乎完全匹配(允许微小差异)
            if gt_val == pred_val:
                correct_counts[field] += 1
            # 如果真实值被完全包含在预测值中，也算正确
            elif gt_val and gt_val in pred_val:
                correct_counts[field] += 1
                print(f"⚠️ 字段 '{field}' 部分匹配: GT='{gt_val}', Pred='{pred_val}'")
    
    accuracies = {field: correct_counts[field] / num_samples for field in fields}
    for field, acc in accuracies.items():
        print(f"字段 '{field}' 的准确率: {acc:.4f}")
    
    success = all(acc >= threshold for acc in accuracies.values())
    print("✅ 验证通过: 所有字段准确度大于等于 95%" if success else "❌ 验证不通过: 存在字段准确度小于 95%")
    
    if result_file:
        result = {
            "Process": True,
            "Results": success,
            "TimePoint": datetime.now().isoformat(),
            "comments": f"字段级准确率: {accuracies}, {'满足' if success else '不满足'} {threshold*100}% 阈值"
        }
        with open(result_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    
    return accuracies, success

def main():
    parser = argparse.ArgumentParser(description="评估 XML 提取结果与 Ground Truth CSV 的准确率。")
    parser.add_argument('--output', type=str, required=True, help="预测 XML 文件路径")
    parser.add_argument('--groundtruth', type=str, required=True, help="Ground truth CSV 文件路径")
    parser.add_argument('--threshold', type=float, default=0.95, help="字段准确率阈值")
    parser.add_argument('--result', type=str, required=False, help="结果保存的 JSONL 文件路径")
    args = parser.parse_args()
    
    evaluate_scraping_xml(args.output, args.groundtruth, args.threshold, args.result)

if __name__ == "__main__":
    main()