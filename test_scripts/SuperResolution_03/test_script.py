import argparse
import numpy as np
from PIL import Image
import json
import os
from datetime import datetime
from scipy.ndimage import sobel
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

def compute_edge_intensity(img_array):
    """
    计算图像的边缘强度（Sobel 梯度）。

    参数:
        img_array (np.ndarray): 输入图像（RGB 或灰度）

    返回:
        np.ndarray: 边缘强度图
    """
    if len(img_array.shape) == 3:
        gray = np.mean(img_array, axis=2).astype(np.float32)
    else:
        gray = img_array.astype(np.float32)
    
    grad_x = sobel(gray, axis=1)
    grad_y = sobel(gray, axis=0)
    edge_intensity = np.sqrt(grad_x**2 + grad_y**2)
    return edge_intensity

def evaluate_super_resolution(input_path, output_path):
    """
    评估超分辨率任务的完成质量，针对 RRDN GANS 模型，接受 2x 或 4x 放大。

    参数:
        input_path (str): 输入低分辨率图像路径（如 baboon.png）
        output_path (str): 输出超分辨率图像路径（如 output_baboon_gans.jpg）

    返回:
        dict: 包含 PSNR、ESI、SSIM 和是否成功的评估结果
    """
    # 加载图像
    input_img = Image.open(input_path).convert('RGB')
    output_img = Image.open(output_path).convert('RGB')
    
    # 转换为 numpy 数组
    input_array = np.array(input_img)
    output_array = np.array(output_img)
    
    # 检查分辨率（允许 2x 或 4x 放大）
    input_h, input_w = input_array.shape[:2]
    output_h, output_w = output_array.shape[:2]
    valid_resolution = (output_h == 2 * input_h and output_w == 2 * input_w) or \
                      (output_h == 4 * input_h and output_w == 4 * input_w)
    if not valid_resolution:
        return {
            'PSNR': 0.0,
            'PSNR Threshold': 20.0,
            'ESI (Edge Strength Improvement)': 0.0,
            'ESI Threshold': 1.1,
            'SSIM': 0.0,
            'SSIM Threshold': 0.5,
            'Success': False,
            'Error': f"Output resolution ({output_w}x{output_h}) is neither 2x nor 4x input ({input_w}x{input_h})"
        }
    
    # 确定放大倍数
    scale = 4 if output_h == 4 * input_h else 2
    
    # 将输入图像上采样到输出分辨率（双线性插值）作为伪参考
    upsampled_img = input_img.resize((output_w, output_h), Image.BILINEAR)
    upsampled_array = np.array(upsampled_img)
    
    # 计算 PSNR
    psnr_value = psnr(upsampled_array, output_array, data_range=255)
    
    # 计算边缘强度
    input_edge = compute_edge_intensity(upsampled_array)
    output_edge = compute_edge_intensity(output_array)
    
    # 保存边缘强度图用于调试
    input_edge_img = Image.fromarray((input_edge / input_edge.max() * 255).astype(np.uint8))
    output_edge_img = Image.fromarray((output_edge / output_edge.max() * 255).astype(np.uint8))
    input_edge_img.save('input_edge.png')
    output_edge_img.save('output_edge.png')
    
    # 计算 ESI（边缘强度提升）
    input_edge_mean = np.mean(input_edge)
    output_edge_mean = np.mean(output_edge)
    esi = output_edge_mean / (input_edge_mean + 1e-10)
    
    # 计算 SSIM
    ssim_value = ssim(upsampled_array, output_array, channel_axis=2, data_range=255)
    
    # 阈值根据放大倍数动态调整
    psnr_threshold = 20.0 if scale == 2 else 18.0
    esi_threshold = 1.1
    ssim_threshold = 0.5
    
    success = psnr_value >= psnr_threshold and esi >= esi_threshold and ssim_value >= ssim_threshold
    
    return {
        'Scale': scale,
        'PSNR': psnr_value,
        'PSNR Threshold': psnr_threshold,
        'ESI (Edge Strength Improvement)': esi,
        'ESI Threshold': esi_threshold,
        'SSIM': ssim_value,
        'SSIM Threshold': ssim_threshold,
        'Success': success
    }

def validate_inputs(input_path, output_path):
    """
    验证输入文件是否存在、非空、格式正确。
    """
    try:
        if not os.path.exists(input_path):
            return False, f"Input file {input_path} does not exist."
        if not os.path.exists(output_path):
            return False, f"Output file {output_path} does not exist."
        
        if os.path.getsize(input_path) == 0:
            return False, f"Input file {input_path} is empty."
        if os.path.getsize(output_path) == 0:
            return False, f"Output file {output_path} is empty."
        
        try:
            with Image.open(input_path) as img:
                img.verify()
            with Image.open(output_path) as img:
                img.verify()
        except Exception as e:
            return False, f"Invalid image format: {str(e)}"
        
        return True, ""
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def save_result_to_jsonl(result_path, process, result, comments):
    """
    将结果保存到 JSONL 文件。
    """
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    record = {
        "Process": process,
        "Result": bool(result),
        "TimePoint": time_point,
        "comments": comments
    }
    
    try:
        with open(result_path, 'a', encoding='utf-8') as f:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + '\n')
    except Exception as e:
        print(f"Failed to save result to {result_path}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Evaluate super-resolution quality for RRDN GANS model, supporting 2x or 4x scaling.')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to input low-resolution image (e.g., baboon.png)')
    parser.add_argument('--output', type=str, required=True, help='Path to output super-resolution image (e.g., output_baboon_gans.jpg)')
    parser.add_argument('--result', type=str, help='Path to JSONL file to save results')
    
    args = parser.parse_args()
    
    process, comments = validate_inputs(args.groundtruth, args.output)
    result_dict = {}
    success = False
    
    if process:
        try:
            result_dict = evaluate_super_resolution(args.groundtruth, args.output)
            success = result_dict.get('Success', False)
            if 'Error' in result_dict:
                comments = result_dict['Error']
                success = False
            else:
                comments = (
                    f"Scale: {result_dict['Scale']}x, "
                    f"PSNR: {result_dict['PSNR']:.3f} "
                    f"(Threshold: {result_dict['PSNR Threshold']}), "
                    f"ESI: {result_dict['ESI (Edge Strength Improvement)']:.3f} "
                    f"(Threshold: {result_dict['ESI Threshold']}), "
                    f"SSIM: {result_dict['SSIM']:.3f} "
                    f"(Threshold: {result_dict['SSIM Threshold']}), "
                    f"Success: {success}"
                )
                if not success:
                    comments += ". Possible issues: Low PSNR (poor pixel similarity), low ESI (insufficient edge enhancement), or low SSIM (structural distortion)."
        except Exception as e:
            process = False
            success = False
            comments = f"Evaluation failed: {str(e)}"
    else:
        success = False
    
    print('Evaluation Results:')
    if process and 'Error' not in result_dict:
        for key, value in result_dict.items():
            if key != 'Error':
                print(f'{key}: {value}')
    else:
        print(f'Error: {comments}')
    
    if args.result:
        save_result_to_jsonl(args.result, process, success, comments)

if __name__ == '__main__':
    main()