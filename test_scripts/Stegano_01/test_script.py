import argparse
import os
import json
import cv2
from datetime import datetime
from stegano import lsb
from skimage.metrics import peak_signal_noise_ratio as compare_psnr

def evaluate_watermark(input_path, watermark, output_path):
    process_success = True
    final_result_success = False
    comments = []
    time_point = datetime.now().isoformat()

    # === Step 0: 输入文件校验 ===
    if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
        comments.append(f"❌ 原图文件不存在或为空：{input_path}")
        process_success = False

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        comments.append(f"❌ 输出图像文件不存在或为空：{output_path}")
        process_success = False

    if process_success:
        try:
            # Step 1: 提取水印
            extracted = lsb.reveal(output_path)
            match = (extracted == watermark)
            comments.append(f"{'✅' if match else '❌'} 提取结果: '{extracted}' | GT: '{watermark}'")

            # Step 2: 计算 PSNR
            original_img = cv2.imread(input_path)
            watermarked_img = cv2.imread(output_path)

            if original_img is None or watermarked_img is None:
                comments.append("❌ 图像读取失败，请确认路径和图像格式。")
                process_success = False
            elif original_img.shape != watermarked_img.shape:
                comments.append("❌ 图像尺寸不一致，无法计算 PSNR。")
                process_success = False
            else:
                psnr = compare_psnr(original_img, watermarked_img)
                comments.append(f"📐 PSNR: {psnr:.2f} dB")
                comments.append(f"🎯 水印检测_match: {'100%' if match else '0%'}")
                comments.append(f"🎯 PSNR ≥ 40.0: {'✅ 满足' if psnr >= 40.0 else '❌ 不满足'}")
                final_result_success = match and (psnr >= 40.0)

        except Exception as e:
            comments.append(f"❌ 执行过程中发生异常: {str(e)}")
            process_success = False

    # 返回结构化结果
    return {
        "Process": process_success,
        "Result": final_result_success,
        "TimePoint": time_point,
        "comments": "\n".join(comments)
    }

def write_to_jsonl(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
        print(f"✅ 测试结果已保存至 {path}")
    except Exception as e:
        print(f"❌ 写入 JSONL 失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取并评估64位水印的准确性与PSNR")
    parser.add_argument("--groundtruth", required=True, help="原始图像路径")
    parser.add_argument("--watermark", required=True, help="期望提取的64位水印（8字符）")
    parser.add_argument("--output", required=True, help="嵌入水印后的图像路径")
    parser.add_argument("--result", help="用于保存结果的 JSONL 路径")

    args = parser.parse_args()
    result = evaluate_watermark(args.groundtruth, args.watermark, args.output)

    if args.result:
        write_to_jsonl(args.result, result)
