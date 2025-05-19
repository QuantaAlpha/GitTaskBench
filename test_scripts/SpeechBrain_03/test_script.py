import jiwer
import argparse
import os
import json
from datetime import datetime

def evaluate_speech_recognition(output_path, groundtruth_path, wer_threshold=0.3):
    """
    评估语音识别效果，使用WER（词错误率）指标。
    
    Args:
        output_path (str): 语音识别生成的文本文件路径
        groundtruth_path (str): 真实标注文本文件路径
        wer_threshold (float): WER阈值（默认0.3，即30%）
    
    Returns:
        dict: 包含WER值和评估结果的字典
    """
    # 读取文本文件
    def read_text_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                # 仅移除首尾空格，保留原始格式
                if not text:
                    raise ValueError(f"File is empty: {file_path}")
                return text
        except UnicodeDecodeError:
            raise ValueError(f"File encoding error, expected UTF-8: {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {str(e)}")

    # 加载输出和真实文本
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

    # 调试：打印原始文本
    print(f"Raw groundtruth: '{groundtruth_text}'")
    print(f"Raw output: '{output_text}'")

    # 验证文本非空
    if not groundtruth_text.strip() or not output_text.strip():
        return {
            'wer': None,
            'threshold': wer_threshold,
            'is_acceptable': False,
            'message': f"Empty text (Groundtruth: '{groundtruth_text}', Output: '{output_text}')"
        }

    # 计算WER
    try:
        # 仅小写转换，保留原始单词分割
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

    # 评估结果
    is_acceptable = wer <= wer_threshold
    result = {
        'wer': float(wer),
        'threshold': float(wer_threshold),
        'is_acceptable': is_acceptable,
        'message': f"WER: {wer*100:.2f}%, {'Acceptable' if is_acceptable else 'Unacceptable'} (Threshold: {wer_threshold*100:.2f}%)"
    }

    return result

def check_file_validity(file_path):
    """检查文件是否存在、非空、格式正确"""
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

    # 检查文件有效性
    comments = []
    process_success = True
    for path in [args.output, args.groundtruth]:
        is_valid, comment = check_file_validity(path)
        if not is_valid:
            process_success = False
            comments.append(comment)

    # 初始化结果字典
    result_dict = {
        "Process": process_success,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }

    # 如果 Process 失败，直接保存结果
    if not process_success:
        result_dict["comments"] = "; ".join(comments)
    else:
        try:
            # 运行评估
            result = evaluate_speech_recognition(
                output_path=args.output,
                groundtruth_path=args.groundtruth,
                wer_threshold=args.threshold
            )

            # 更新结果
            result_dict["Result"] = result['is_acceptable']
            result_dict["comments"] = result['message']
            print(result['message'])
        except Exception as e:
            result_dict["Result"] = False
            result_dict["comments"] = f"Evaluation failed: {str(e)}"
            comments.append(str(e))

    # 如果指定了 result 文件路径，保存到 JSONL
    if args.result:
        try:
            # 确保布尔值序列化正确
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
            raise  # 抛出异常以确保脚本退出码非零

if __name__ == "__main__":
    main()