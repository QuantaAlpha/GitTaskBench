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
    """从视频中提取帧，限制最大帧数以提高效率"""
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
    """计算输入和输出帧之间的平均SSIM"""
    ssim_scores = []
    for in_frame, out_frame in zip(input_frames, output_frames):
        # 如果尺寸不匹配，调整帧大小
        min_shape = (min(in_frame.shape[0], out_frame.shape[0]), 
                     min(in_frame.shape[1], out_frame.shape[1]))
        in_frame = cv2.resize(in_frame, min_shape[::-1])
        out_frame = cv2.resize(out_frame, min_shape[::-1])
        # 转换为灰度图以计算SSIM
        in_gray = cv2.cvtColor(in_frame, cv2.COLOR_RGB2GRAY)
        out_gray = cv2.cvtColor(out_frame, cv2.COLOR_RGB2GRAY)
        score = ssim(in_gray, out_gray, data_range=255)
        ssim_scores.append(score)
    return np.mean(ssim_scores) if ssim_scores else 0.0

def get_inception_features(frames, model, transform, device):
    """提取Inception V3特征用于FID计算"""
    features = []
    for frame in frames:
        img = cv2.resize(frame, (299, 299))
        img = transform(img).unsqueeze(0).to(device)
        with torch.no_grad():
            feat = model(img).squeeze().cpu().numpy()
        features.append(feat)
    return np.array(features)

def compute_fid(input_frames, output_frames):
    """使用Inception V3计算输入和输出帧的FID"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    inception = models.inception_v3(pretrained=True, transform_input=False).eval().to(device)
    
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    input_features = get_inception_features(input_frames, inception, transform, device)
    output_features = get_inception_features(output_frames, inception, transform, device)
    
    # 计算均值和协方差
    mu1, sigma1 = np.mean(input_features, axis=0), np.cov(input_features, rowvar=False)
    mu2, sigma2 = np.mean(output_features, axis=0), np.cov(output_features, rowvar=False)
    
    # 计算FID
    diff = mu1 - mu2
    covmean = sqrtm(sigma1.dot(sigma2))
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    fid = diff.dot(diff) + np.trace(sigma1 + sigma2 - 2 * covmean)
    return fid

def evaluate_animeganv3(input_video, output_video, ssim_threshold=0.7, fid_threshold=400):
    """使用SSIM和FID评估AnimeGANv3风格化效果"""
    messages = []
    messages.append(f"正在评估视频：\n输入视频：{input_video}\n输出视频：{output_video}")
    
    # 提取帧
    input_frames = extract_frames(input_video)
    output_frames = extract_frames(output_video)
    
    if len(input_frames) == 0 or len(output_frames) == 0:
        messages.append("错误：无法从一个或两个视频中提取帧。")
        return False, "\n".join(messages)
    
    if len(input_frames) != len(output_frames):
        messages.append("警告：输入和输出视频的帧数不同。")
        min_frames = min(len(input_frames), len(output_frames))
        input_frames = input_frames[:min_frames]
        output_frames = output_frames[:min_frames]
    
    # 计算SSIM
    avg_ssim = compute_ssim(input_frames, output_frames)
    messages.append(f"平均SSIM：{avg_ssim:.4f}")
    
    # 计算FID
    fid_score = compute_fid(input_frames, output_frames)
    messages.append(f"FID得分：{fid_score:.2f}")
    
    # 与阈值比较
    ssim_pass = avg_ssim >= ssim_threshold
    fid_pass = fid_score <= fid_threshold
    success = ssim_pass and fid_pass
    
    result_message = f"\n评估结果：\n"
    result_message += f"SSIM（≥ {ssim_threshold}）：{'通过' if ssim_pass else '未通过'} ({avg_ssim:.4f})\n"
    result_message += f"FID（≤ {fid_threshold}）：{'通过' if fid_pass else '未通过'} ({fid_score:.2f})\n"
    result_message += f"总体成功：{'是' if success else '否'}"
    messages.append(result_message)
    
    return success, "\n".join(messages)

def is_valid_video_file(file_path):
    """检查文件是否存在、非空且为有效视频格式（.mp4）"""
    if not os.path.exists(file_path):
        return False, f"文件 {file_path} 不存在。"
    if os.path.getsize(file_path) == 0:
        return False, f"文件 {file_path} 为空。"
    if not file_path.lower().endswith('.mp4'):
        return False, f"文件 {file_path} 格式不正确，仅支持 .mp4。"
    return True, ""

def main():
    parser = argparse.ArgumentParser(description="评估AnimeGANv3视频风格化效果")
    parser.add_argument("-i", "--groundtruth", required=True, help="输入视频文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出视频文件路径")
    parser.add_argument("--ssim_threshold", type=float, default=0.7, help="SSIM成功阈值")
    parser.add_argument("--fid_threshold", type=float, default=400.0, help="FID成功阈值")
    parser.add_argument("--result", help="保存结果的JSONL文件路径")
    
    args = parser.parse_args()
    
    # 收集所有输出消息
    messages = []
    success = False
    process_valid = True
    
    # 验证输入文件
    input_valid, input_error = is_valid_video_file(args.groundtruth)
    output_valid, output_error = is_valid_video_file(args.output)
    
    if not input_valid:
        messages.append(input_error)
        process_valid = False
    if not output_valid:
        messages.append(output_error)
        process_valid = False
    
    # 如果输入有效，运行评估
    if process_valid:
        success, eval_message = evaluate_animeganv3(
            args.groundtruth,
            args.output,
            args.ssim_threshold, 
            args.fid_threshold
        )
        messages.append(eval_message)
    else:
        messages.append("由于输入文件验证失败，未运行评估。")
    
    # 打印所有消息
    print("\n".join(messages))
    
    # 如果指定了 --result，保存到 JSONL
# 在main()函数中修改结果保存部分：
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
                f.write(json_line + '\n')  # 确保换行追加
        except Exception as e:
            print(f"错误：无法保存结果到 {args.result}，原因：{str(e)}")

    
if __name__ == "__main__":
    main()