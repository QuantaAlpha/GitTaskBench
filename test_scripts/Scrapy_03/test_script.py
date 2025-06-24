import argparse
import os
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime


def check_file_valid(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        print(f"❌ File does not exist: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ File is empty: {file_path}")
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
    """Extract content from XML file, filtering out possible comments and non-XML content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Keep XML declaration if found, otherwise add one
        xml_decl_match = re.search(r'<\?xml[^>]+\?>', content)
        if xml_decl_match:
            xml_decl = xml_decl_match.group(0)
            content = content[xml_decl_match.end():]
        else:
            xml_decl = '<?xml version="1.0" encoding="UTF-8"?>'

        # Remove XML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

        # Remove illegal XML characters
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)

        # Find content between first < and last > (remove possible non-XML prefixes/suffixes)
        start_idx = content.find('<')
        end_idx = content.rfind('>')
        if start_idx >= 0 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]

        # Ensure there's a root element
        if not re.search(r'<\w+[^>]*>.*</\w+>', content, re.DOTALL):
            content = f"<root>{content}</root>"

        return xml_decl + content
    except Exception as e:
        print(f"❌ Failed to read XML file: {e}")
        return None


def parse_xml(file_path):
    """Generic XML parser that identifies various possible structures"""
    try:
        xml_content = extract_xml_content(file_path)
        if not xml_content:
            return []

        # Try to parse XML
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"❌ XML parse error, attempting repair: {e}")
        try:
            # Try to handle incomplete XML
            xml_content = re.sub(r'<\?xml[^>]+\?>', '', xml_content)
            xml_content = f"<root>{xml_content}</root>"
            root = ET.fromstring(xml_content)
        except ET.ParseError as e2:
            print(f"❌ XML repair failed: {e2}")
            # Final attempt with more aggressive repair
            try:
                pattern = r'<(.*?)>(.*?)</(.*?)>'
                matches = re.findall(pattern, xml_content, re.DOTALL)
                items_xml = ''.join([f'<item>{m[1]}</item>' for m in matches if len(m) >= 2])
                root = ET.fromstring(f"<root>{items_xml}</root>")
            except:
                print("❌ All XML repair attempts failed")
                return []

    records = []

    # Get all possible item elements
    # Common tag patterns: quote, item, entry, record, etc.
    item_tags = ['quote', 'item', 'entry', 'record', 'row', 'data']

    # Try to find direct children of root element
    direct_children = list(root)

    # If there are multiple direct children with similar structure, they might be our items
    candidates = []
    if len(direct_children) > 1:
        # Check if these elements have similar structure
        first_child_tags = set([child.tag for child in direct_children[0]] if len(direct_children) > 0 else [])
        if all(set([child.tag for child in elem]) == first_child_tags for elem in direct_children[1:]):
            candidates.extend(direct_children)

    # If no suitable direct children found, try predefined item tags
    if not candidates:
        for tag in item_tags:
            items = root.findall(f".//{tag}")
            if items:
                candidates.extend(items)
                break

    # If still not found, try to find any element containing author and text sub-elements
    if not candidates:
        for elem in root.findall(".//*"):
            has_author = any(child.tag == 'author' or 'author' in child.tag.lower() for child in elem)
            has_text = any(child.tag == 'text' or 'text' in child.tag.lower() for child in elem)
            if has_author and has_text:
                candidates.append(elem)

    # Extract author and text information from candidate items
    for item in candidates:
        author_content = ""
        text_content = ""

        # Method 1: Directly look for specific tags
        for child in item:
            if child.tag.lower() == 'author' or 'author' in child.tag.lower():
                author_content = clean_text(child.text)
            elif child.tag.lower() == 'text' or 'text' in child.tag.lower() or child.tag.lower() == 'quote':
                text_content = clean_text(child.text)

        # Method 2: Look for elements containing specific keywords
        if not author_content or not text_content:
            for elem in item.findall(".//*"):
                if (elem.tag.lower() == 'author' or 'author' in elem.tag.lower()) and not author_content:
                    author_content = clean_text(elem.text)
                elif (
                        elem.tag.lower() == 'text' or 'text' in elem.tag.lower() or 'quote' in elem.tag.lower() or 'content' in elem.tag.lower()) and not text_content:
                    text_content = clean_text(elem.text)

        # Method 3: Look in attributes
        for attr_name, attr_value in item.attrib.items():
            if ('author' in attr_name.lower()) and not author_content:
                author_content = clean_text(attr_value)
            elif (
                    'text' in attr_name.lower() or 'quote' in attr_name.lower() or 'content' in attr_name.lower()) and not text_content:
                text_content = clean_text(attr_value)

        # Method 4: If item only has plain text with specific pattern, try to extract
        if (not author_content or not text_content) and item.text and item.text.strip():
            # Try to match author-quote pattern like "Author Name: 'Quote text'"
            author_quote_match = re.search(r'([^:]+):\s*[\'"](.+?)[\'"]', item.text.strip())
            if author_quote_match:
                if not author_content:
                    author_content = clean_text(author_quote_match.group(1))
                if not text_content:
                    text_content = clean_text(author_quote_match.group(2))

        # Only include records with content
        if author_content and text_content:
            records.append({
                "author": author_content,
                "text": text_content
            })

    # If no records found with above methods, try direct text extraction
    if not records:
        print("⚠️ No records found with standard parsing methods, attempting direct text extraction...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to match author and quote patterns
            pattern = r'<(author|text)>(.*?)</(author|text)>'
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)

            authors = [clean_text(m[1]) for m in matches if m[0].lower() == 'author' and m[2].lower() == 'author']
            texts = [clean_text(m[1]) for m in matches if m[0].lower() == 'text' and m[2].lower() == 'text']

            # If equal number of authors and texts found, assume they are pairs
            if len(authors) == len(texts) and len(authors) > 0:
                records = [{"author": a, "text": t} for a, t in zip(authors, texts)]
        except Exception as e:
            print(f"❌ Text extraction failed: {e}")

    return records


def find_best_matches(preds, gts):
    """Find best matches between predictions and ground truth"""
    matched_pairs = []
    remaining_preds = list(range(len(preds)))

    for i, gt_item in enumerate(gts):
        best_score = -1
        best_idx = -1

        for j in remaining_preds:
            pred_item = preds[j]
            score = 0

            # Score based on text similarity
            for field in ["author", "text"]:
                gt_val = gt_item.get(field, "").lower()
                pred_val = pred_item.get(field, "").lower()

                # Exact match
                if gt_val == pred_val:
                    score += 2
                # Partial match (one contains the other)
                elif gt_val in pred_val or pred_val in gt_val:
                    score += 1

            if score > best_score:
                best_score = score
                best_idx = j

        if best_idx >= 0:
            matched_pairs.append((i, best_idx))
            remaining_preds.remove(best_idx)
        else:
            # If no match found, use default index matching
            default_idx = i if i < len(preds) else 0
            matched_pairs.append((i, default_idx))

    return matched_pairs


def evaluate_scraping_xml(pred_file, gt_file, threshold=0.95, result_file=None):
    if not check_file_valid(pred_file) or not check_file_valid(gt_file):
        return {}, False

    preds = parse_xml(pred_file)
    gts = parse_xml(gt_file)  # Changed from parse_csv to parse_xml

    if not preds:
        print("❌ Could not extract valid records from prediction XML")
        if result_file:
            result = {
                "Process": True,
                "Result": False,
                "TimePoint": datetime.now().isoformat(),
                "comments": "Prediction XML parsing failed, could not extract valid records"
            }
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
        return {}, False

    if not gts:
        print("❌ Could not extract valid records from ground truth XML")
        if result_file:
            result = {
                "Process": True,
                "Result": False,
                "TimePoint": datetime.now().isoformat(),
                "comments": "Ground truth XML parsing failed, could not extract valid records"
            }
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
        return {}, False

    print(f"✓ Extracted {len(preds)} records from prediction XML")
    print(f"✓ Extracted {len(gts)} records from ground truth XML")

    for i, record in enumerate(preds[:3]):  # Only show first 3 as examples
        print(f"  Prediction Record {i + 1}: Author='{record['author']}', Text='{record['text'][:30]}...'")
    if len(preds) > 3:
        print(f"  ... plus {len(preds) - 3} more prediction records")

    if len(preds) != len(gts):
        print(
            f"⚠️ Prediction and ground truth lengths differ (predicted {len(preds)}, truth {len(gts)}), finding best matches.")

    num_samples = min(len(preds), len(gts))
    if num_samples == 0:
        print("❌ Error: No data to compare.")
        return {}, False

    fields = ["author", "text"]
    correct_counts = {field: 0 for field in fields}

    # Find best matches between predictions and ground truth
    matched_pairs = find_best_matches(preds, gts[:num_samples])

    for gt_idx, pred_idx in matched_pairs:
        for field in fields:
            gt_val = clean_text(gts[gt_idx].get(field, "")).lower()
            pred_val = clean_text(preds[pred_idx].get(field, "")).lower()

            # Exact match or near-exact match (allowing minor differences)
            if gt_val == pred_val:
                correct_counts[field] += 1
            # If ground truth is fully contained in prediction, also count as correct
            elif gt_val and gt_val in pred_val:
                correct_counts[field] += 1
                print(f"⚠️ Field '{field}' partial match: GT='{gt_val}', Pred='{pred_val}'")

    accuracies = {field: correct_counts[field] / num_samples for field in fields}
    for field, acc in accuracies.items():
        print(f"Field '{field}' accuracy: {acc:.4f}")

    success = all(acc >= threshold for acc in accuracies.values())
    print(
        f"✅ Validation passed: All fields accuracy >= {threshold * 100}%" if success
        else f"❌ Validation failed: Some fields accuracy < {threshold * 100}%")

    if result_file:
        # Ensure directory exists
        os.makedirs(os.path.dirname(result_file), exist_ok=True)

        result = {
            "Process": True,
            "Results": success,
            "TimePoint": datetime.now().isoformat(),
            "comments": f"Field-level accuracy: {accuracies}, {'meets' if success else 'does not meet'} {threshold * 100}% threshold"
        }
        with open(result_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")

    return accuracies, success


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate accuracy of XML extraction results against Ground Truth XML.")
    parser.add_argument('--output', type=str, required=True, help="Prediction XML file path")
    parser.add_argument('--groundtruth', type=str, required=True, help="Ground truth XML file path")
    parser.add_argument('--threshold', type=float, default=0.95, help="Field accuracy threshold")
    parser.add_argument('--result', type=str, required=False, help="Output JSONL file path for results")
    args = parser.parse_args()

    evaluate_scraping_xml(args.output, args.groundtruth, args.threshold, args.result)


if __name__ == "__main__":
    main()