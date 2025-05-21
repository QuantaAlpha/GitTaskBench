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

    # Timestamp
    time_point = datetime.now().isoformat()

    # Check input files
    if not os.path.exists(original_path) or os.path.getsize(original_path) == 0:
        comments.append(f"Error: Original image file '{original_path}' does not exist or is empty.")
        process_status = False
    if not os.path.exists(watermarked_path) or os.path.getsize(watermarked_path) == 0:
        comments.append(f"Error: Watermarked image file '{watermarked_path}' does not exist or is empty.")
        process_status = False

    if process_status:
        bgr_original = cv2.imread(original_path)
        bgr_encoded  = cv2.imread(watermarked_path)
        if bgr_original is None or bgr_encoded is None:
            comments.append("Error: Failed to read images, please check if files are corrupted or in correct format.")
            process_status = False

    if process_status:
        try:
            decoder       = WatermarkDecoder('bytes', len(watermark_text)*8)
            decoded_bytes = decoder.decode(bgr_encoded, 'dwtDct')
            extracted_text= decoded_bytes.decode('utf-8', errors='ignore')
            is_match      = (extracted_text == watermark_text)

            comments.append(f"{'✅' if is_match else '❌'} Extraction result: '{extracted_text}' | GT: '{watermark_text}'")
            psnr_value = compare_psnr(bgr_original, bgr_encoded)
            comments.append(f"📐 PSNR: {psnr_value:.2f} dB")

            # Metrics
            match_rate     = '100%' if is_match else '0%'
            psnr_satisfied = psnr_value >= 30.0
            comments.append(f"🎯 Watermark detection_match: {match_rate}")
            comments.append(f"🎯 PSNR ≥ 30.0: {'✅ Satisfied' if psnr_satisfied else '❌ Not satisfied'}")

            final_result_status = is_match and psnr_satisfied
            comments.append(f"Final evaluation result: Watermark match={is_match}, PSNR satisfied={psnr_satisfied}")

        except Exception as e:
            comments.append(f"Exception occurred during watermark processing or evaluation: {e}")
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
    Append single result to JSONL file:
    Each run appends one JSON line.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            # Add default=str to handle non-serializable types with str()
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
        print(f"✅ Result appended to JSONL file: {file_path}")
    except Exception as e:
        print(f"❌ Error occurred while writing to JSONL file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract and verify blind watermark, calculate image quality, and store results as JSONL")
    parser.add_argument("--groundtruth",     required=True, help="Path to original image")
    parser.add_argument("--output",    required=True, help="Path to watermarked image")
    parser.add_argument("--watermark", required=True, help="Expected watermark content to extract")
    parser.add_argument("--result",    help="File path to store JSONL results")

    args = parser.parse_args()

    evaluation_result = evaluate_watermark(
        args.groundtruth, args.watermark, args.output)

    if args.result:
        write_to_jsonl(args.result, evaluation_result)