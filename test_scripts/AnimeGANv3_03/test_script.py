import argparse
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from scipy.linalg import sqrtm
import os
import json
from datetime import datetime


def extract_frames(video_path, max_frames=100):
    """Extract frames from video, limiting maximum frames for efficiency"""
    cap = cv2.VideoCapture(video_path)
    frames = []
    count = 0
    while cap.isOpened() and count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)
        count += 1
    cap.release()
    return frames


def compute_ssim(input_frames, output_frames):
    """Calculate average SSIM between input and output frames"""
    ssim_scores = []
    for in_frame, out_frame in zip(input_frames, output_frames):
        # Resize frames if dimensions don't match
        min_shape = (min(in_frame.shape[0], out_frame.shape[0]),
                     min(in_frame.shape[1], out_frame.shape[1]))
        in_frame = cv2.resize(in_frame, min_shape[::-1])
        out_frame = cv2.resize(out_frame, min_shape[::-1])
        # Convert to grayscale for SSIM calculation
        in_gray = cv2.cvtColor(in_frame, cv2.COLOR_RGB2GRAY)
        out_gray = cv2.cvtColor(out_frame, cv2.COLOR_RGB2GRAY)
        score = ssim(in_gray, out_gray, data_range=255)
        ssim_scores.append(score)
    return np.mean(ssim_scores) if ssim_scores else 0.0


def get_inception_features(frames, model, transform, device):
    """Extract Inception V3 features for FID calculation"""
    features = []
    for frame in frames:
        img = cv2.resize(frame, (299, 299))
        img = transform(img).unsqueeze(0).to(device)
        with torch.no_grad():
            feat = model(img).squeeze().cpu().numpy()
        features.append(feat)
    return np.array(features)


def compute_fid(input_frames, output_frames):
    """Calculate FID between input and output frames using Inception V3"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    inception = models.inception_v3(pretrained=True, transform_input=False).eval().to(device)

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    input_features = get_inception_features(input_frames, inception, transform, device)
    output_features = get_inception_features(output_frames, inception, transform, device)

    # Calculate mean and covariance
    mu1, sigma1 = np.mean(input_features, axis=0), np.cov(input_features, rowvar=False)
    mu2, sigma2 = np.mean(output_features, axis=0), np.cov(output_features, rowvar=False)

    # Calculate FID
    diff = mu1 - mu2
    covmean = sqrtm(sigma1.dot(sigma2))
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    fid = diff.dot(diff) + np.trace(sigma1 + sigma2 - 2 * covmean)
    return fid


def evaluate_animeganv3(input_video, output_video, ssim_threshold=0.7, fid_threshold=400):
    """Evaluate AnimeGANv3 stylization effect using SSIM and FID"""
    messages = []
    messages.append(f"Evaluating videos:\nInput video: {input_video}\nOutput video: {output_video}")

    # Extract frames
    input_frames = extract_frames(input_video)
    output_frames = extract_frames(output_video)

    if len(input_frames) == 0 or len(output_frames) == 0:
        messages.append("Error: Failed to extract frames from one or both videos.")
        return False, "\n".join(messages)

    if len(input_frames) != len(output_frames):
        messages.append("Warning: Input and output videos have different frame counts.")
        min_frames = min(len(input_frames), len(output_frames))
        input_frames = input_frames[:min_frames]
        output_frames = output_frames[:min_frames]

    # Calculate SSIM
    avg_ssim = compute_ssim(input_frames, output_frames)
    messages.append(f"Average SSIM: {avg_ssim:.4f}")

    # Calculate FID
    fid_score = compute_fid(input_frames, output_frames)
    messages.append(f"FID score: {fid_score:.2f}")

    # Compare with thresholds
    ssim_pass = avg_ssim >= ssim_threshold
    fid_pass = fid_score <= fid_threshold
    success = ssim_pass and fid_pass

    result_message = f"\nEvaluation results:\n"
    result_message += f"SSIM (≥ {ssim_threshold}): {'Pass' if ssim_pass else 'Fail'} ({avg_ssim:.4f})\n"
    result_message += f"FID (≤ {fid_threshold}): {'Pass' if fid_pass else 'Fail'} ({fid_score:.2f})\n"
    result_message += f"Overall success: {'Yes' if success else 'No'}"
    messages.append(result_message)

    return success, "\n".join(messages)


def is_valid_video_file(file_path):
    """Check if file exists, is non-empty and has valid video format (.mp4)"""
    if not os.path.exists(file_path):
        return False, f"File {file_path} does not exist."
    if os.path.getsize(file_path) == 0:
        return False, f"File {file_path} is empty."
    if not file_path.lower().endswith('.mp4'):
        return False, f"File {file_path} has incorrect format, only .mp4 supported."
    return True, ""


def main():
    parser = argparse.ArgumentParser(description="Evaluate AnimeGANv3 video stylization effect")
    parser.add_argument("-i", "--groundtruth", required=True, help="Input video file path")
    parser.add_argument("-o", "--output", required=True, help="Output video file path")
    parser.add_argument("--ssim_threshold", type=float, default=0.7, help="SSIM success threshold")
    parser.add_argument("--fid_threshold", type=float, default=400.0, help="FID success threshold")
    parser.add_argument("--result", help="JSONL file path to save results")

    args = parser.parse_args()

    # Collect all output messages
    messages = []
    success = False
    process_valid = True

    # Validate input files
    input_valid, input_error = is_valid_video_file(args.groundtruth)
    output_valid, output_error = is_valid_video_file(args.output)

    if not input_valid:
        messages.append(input_error)
        process_valid = False
    if not output_valid:
        messages.append(output_error)
        process_valid = False

    # If inputs are valid, run evaluation
    if process_valid:
        success, eval_message = evaluate_animeganv3(
            args.groundtruth,
            args.output,
            args.ssim_threshold,
            args.fid_threshold
        )
        messages.append(eval_message)
    else:
        messages.append("Evaluation not run due to input file validation failure.")

    # Print all messages
    print("\n".join(messages))

    # If --result is specified, save to JSONL
    # Modified result saving section in main() function:
    if args.result:
        result_entry = {
            "Process": process_valid,
            "Result": success,
            "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "comments": "\n".join(messages)
        }
        try:
            os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)
            with open(args.result, 'a', encoding='utf-8') as f:
                json_line = json.dumps(result_entry, ensure_ascii=False, default=str)
                f.write(json_line + '\n')  # Ensure newline append
        except Exception as e:
            print(f"Error: Failed to save results to {args.result}, reason: {str(e)}")


if __name__ == "__main__":
    main()