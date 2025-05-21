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

    # === Step 0: Input file validation ===
    if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
        comments.append(f"❌ Original image file missing or empty: {input_path}")
        process_success = False

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        comments.append(f"❌ Watermarked image file missing or empty: {output_path}")
        process_success = False

    if process_success:
        try:
            # Step 1: Extract watermark
            extracted = lsb.reveal(output_path)
            match = (extracted == watermark)
            comments.append(f"{'✅' if match else '❌'} Extraction result: '{extracted}' | Expected: '{watermark}'")

            # Step 2: Calculate PSNR
            original_img = cv2.imread(input_path)
            watermarked_img = cv2.imread(output_path)

            if original_img is None or watermarked_img is None:
                comments.append("❌ Failed to read images, please verify paths and formats")
                process_success = False
            elif original_img.shape != watermarked_img.shape:
                comments.append("❌ Image dimensions don't match, cannot compute PSNR")
                process_success = False
            else:
                psnr = compare_psnr(original_img, watermarked_img)
                comments.append(f"📐 PSNR: {psnr:.2f} dB")
                comments.append(f"🎯 Watermark match: {'100%' if match else '0%'}")
                comments.append(f"🎯 PSNR ≥ 40.0: {'✅ Met' if psnr >= 40.0 else '❌ Not met'}")
                final_result_success = match and (psnr >= 40.0)

        except Exception as e:
            comments.append(f"❌ Exception occurred during execution: {str(e)}")
            process_success = False

    # Return structured results
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
        print(f"✅ Test results saved to {path}")
    except Exception as e:
        print(f"❌ Failed to write JSONL: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and evaluate hidden message accuracy and PSNR")
    parser.add_argument("--groundtruth", required=True, help="Path to original image")
    parser.add_argument("--watermark", required=True, help="Expected 64-bit watermark (8 characters)")
    parser.add_argument("--output", required=True, help="Path to watermarked image")
    parser.add_argument("--result", help="Path to save results in JSONL format")

    args = parser.parse_args()
    result = evaluate_watermark(args.groundtruth, args.watermark, args.output)

    if args.result:
        write_to_jsonl(args.result, result)