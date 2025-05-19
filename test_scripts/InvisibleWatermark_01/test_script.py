import argparse
import cv2
import json
import os
from datetime import datetime
from imwatermark import WatermarkDecoder
from skimage.metrics import peak_signal_noise_ratio as compare_psnr

def evaluate_watermark(original_path, watermark_text, watermarked_path):
    process_status = True
    final_result_status = False
    comments = []

    # 时间戳
    time_point = datetime.now().isoformat()

    # 检查输入文件
    if not os.path.exists(original_path) or os.path.getsize(original_path) == 0:
        comments.append(f"错误：原始图像文件 '{original_path}' 不存在或为空。")
        process_status = False
    if not os.path.exists(watermarked_path) or os.path.getsize(watermarked_path) == 0:
        comments.append(f"错误：水印图像文件 '{watermarked_path}' 不存在或为空。")
        process_status = False

    if process_status:
        bgr_original = cv2.imread(original_path)
        bgr_encoded  = cv2.imread(watermarked_path)
        if bgr_original is None or bgr_encoded is None:
            comments.append("错误：读取图像失败，请确认文件是否损坏或格式是否正确。")
            process_status = False

    if process_status:
        try:
            decoder       = WatermarkDecoder('bytes', len(watermark_text)*8)
            decoded_bytes = decoder.decode(bgr_encoded, 'dwtDct')
            extracted_text= decoded_bytes.decode('utf-8', errors='ignore')
            is_match      = (extracted_text == watermark_text)

            comments.append(f"{'✅' if is_match else '❌'} 提取结果: '{extracted_text}' | GT: '{watermark_text}'")
            psnr_value = compare_psnr(bgr_original, bgr_encoded)
            comments.append(f"📐 PSNR: {psnr_value:.2f} dB")

            # 指标
            match_rate     = '100%' if is_match else '0%'
            psnr_satisfied = psnr_value >= 30.0
            comments.append(f"🎯 水印检测_match: {match_rate}")
            comments.append(f"🎯 PSNR ≥ 30.0: {'✅ 满足' if psnr_satisfied else '❌ 不满足'}")

            final_result_status = is_match and psnr_satisfied
            comments.append(f"最终评估结果：水印匹配={is_match}, PSNR满足={psnr_satisfied}")

        except Exception as e:
            comments.append(f"水印处理或评估过程中发生异常: {e}")
            final_result_status = False

    output_data = {
        "Process":   process_status,
        "Result":    final_result_status,
        "TimePoint": time_point,
        "Comments":  "\n".join(comments)
    }
    print(output_data["Comments"])
    return output_data

def write_to_jsonl(file_path, data):
    """
    将单条结果以 JSONL 形式追加到文件末尾：
    每运行一次，append 一行 JSON。
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            # 增加 default=str，遇到无法直接序列化的类型就 str() 处理
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
        print(f"✅ 结果已追加到 JSONL 文件: {file_path}")
    except Exception as e:
        print(f"❌ 写入 JSONL 文件时发生错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="提取并验证盲水印，计算图像质量，并将结果存储为 JSONL")
    parser.add_argument("--groundtruth",     required=True, help="原始图像路径")
    parser.add_argument("--output",    required=True, help="水印图像路径")
    parser.add_argument("--watermark", required=True, help="期望提取的水印内容")
    parser.add_argument("--result",    help="用于存储 JSONL 结果的文件路径")

    args = parser.parse_args()

    evaluation_result = evaluate_watermark(
        args.groundtruth, args.watermark, args.output)

    if args.result:
        write_to_jsonl(args.result, evaluation_result)
