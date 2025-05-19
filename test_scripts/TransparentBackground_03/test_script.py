import argparse
import numpy as np
from PIL import Image
import json
import os
from datetime import datetime
from scipy.ndimage import sobel

def compute_edge_intensity(img_array):
    """
    计算图像的边缘强度（Sobel 梯度）。

    参数:
        img_array (np.ndarray): 输入图像（RGB 或灰度）

    返回:
        np.ndarray: 边缘强度图
    """
    # 转换为灰度
    if len(img_array.shape) == 3:
        gray = np.mean(img_array, axis=2).astype(np.float32)
    else:
        gray = img_array.astype(np.float32)
    
    # 计算 Sobel 梯度
    grad_x = sobel(gray, axis=1)
    grad_y = sobel(gray, axis=0)
    edge_intensity = np.sqrt(grad_x**2 + grad_y**2)
    return edge_intensity

def evaluate_blur_background(input_path, output_path):
    """
    评估模糊背景替换任务的完成质量，无需预训练模型。

    参数:
        input_path (str): 输入图像路径
        output_path (str): 输出图像路径（模糊背景）

    返回:
        dict: 包含 BBI、FSP 和是否成功的评估结果
    """
    # 加载图像
    input_img = Image.open(input_path).convert('RGB')
    output_img = Image.open(output_path).convert('RGB')
    
    # 转换为 numpy 数组
    input_array = np.array(input_img)
    output_array = np.array(output_img)
    
    # 计算输出图像的边缘强度
    edge_intensity = compute_edge_intensity(output_array)
    
    # 分割背景和前景（基于边缘强度）
    edge_threshold = np.percentile(edge_intensity, 50)  # 中位数作为阈值
    background_mask = edge_intensity <= edge_threshold  # 低边缘强度为背景
    foreground_mask = edge_intensity > edge_threshold   # 高边缘强度为前景
    
    # 保存掩码用于调试
    background_mask_img = Image.fromarray(background_mask.astype(np.uint8) * 255)

    foreground_mask_img = Image.fromarray(foreground_mask.astype(np.uint8) * 255)

    
    # 指标 1：背景模糊度 (BBI)
    # 计算背景区域的平均边缘强度（越低越模糊）
    background_edges = edge_intensity[background_mask]
    bbi = np.mean(background_edges) if background_edges.size > 0 else float('inf')
    
    # 指标 2：前景清晰度保持 (FSP)
    # 比较输入和输出图像前景区域的边缘强度差异
    input_edge_intensity = compute_edge_intensity(input_array)
    input_foreground_edges = input_edge_intensity[foreground_mask]
    output_foreground_edges = edge_intensity[foreground_mask]
    
    if input_foreground_edges.size == 0 or output_foreground_edges.size == 0:
        fsp = float('inf')  # 无前景像素，任务失败
    else:
        input_mean_edge = np.mean(input_foreground_edges)
        output_mean_edge = np.mean(output_foreground_edges)
        fsp = abs(input_mean_edge - output_mean_edge) / (input_mean_edge + 1e-10)  # 相对差异
    
    # 判断任务是否成功
    bbi_threshold = 20  # 背景边缘强度阈值（低表示模糊）
    fsp_threshold = 0.2  # 前景清晰度变化阈值
    success = bbi <= bbi_threshold and fsp <= fsp_threshold
    
    # 返回结果
    return {
        'BBI (Background Blur Intensity)': bbi,
        'BBI Threshold': bbi_threshold,
        'FSP (Foreground Sharpness Preservation)': fsp,
        'FSP Threshold': fsp_threshold,
        'Success': success
    }

def validate_inputs(input_path, output_path):
    """
    验证输入文件是否存在、非空、格式正确。

    返回:
        tuple: (bool, str) - (是否有效, 错误信息或空字符串)
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(input_path):
            return False, f"Input file {input_path} does not exist."
        if not os.path.exists(output_path):
            return False, f"Output file {output_path} does not exist."
        
        # 检查文件是否非空
        if os.path.getsize(input_path) == 0:
            return False, f"Input file {input_path} is empty."
        if os.path.getsize(output_path) == 0:
            return False, f"Output file {output_path} is empty."
        
        # 检查文件格式（尝试打开图像）
        try:
            with Image.open(input_path) as img:
                img.verify()  # 验证图像格式
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

    参数:
        result_path (str): JSONL 文件路径
        process (bool): 输入参数是否有效
        result (bool): 评估是否成功
        comments (str): 备注信息
    """
    # 生成时间戳
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    record = {
        "Process": bool(process),  # 确保是布尔值
        "Result": bool(result),    # 确保是布尔值
        "TimePoint": time_point,
        "comments": comments
    }
    
    # 以追加模式写入 JSONL
    try:
        with open(result_path, 'a', encoding='utf-8') as f:
            json_line = json.dumps(record, ensure_ascii=False, default=str)
            f.write(json_line + '\n')
    except Exception as e:
        print(f"Failed to save result to {result_path}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Evaluate blur background replacement quality without pretrained model.')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to input image')
    parser.add_argument('--output', type=str, required=True, help='Path to output image (blur background)')
    parser.add_argument('--result', type=str, help='Path to JSONL file to save results')
    
    args = parser.parse_args()
    
    # 验证输入参数
    process, comments = validate_inputs(args.groundtruth, args.output)
    
    # 初始化结果
    result_dict = {}
    success = False
    
    # 如果输入有效，运行评估
    if process:
        try:
            result_dict = evaluate_blur_background(args.groundtruth, args.output)
            success = result_dict['Success']
            comments = (
                f"BBI: {result_dict['BBI (Background Blur Intensity)']:.3f} "
                f"(Threshold: {result_dict['BBI Threshold']}), "
                f"FSP: {result_dict['FSP (Foreground Sharpness Preservation)']:.3f} "
                f"(Threshold: {result_dict['FSP Threshold']}), "
                f"Success: {success}"
            )
            if not success:
                comments += ". Possible issues: BBI too high (background not blurred enough) or FSP too high (foreground clarity degraded)."
        except Exception as e:
            process = False
            success = False
            comments = f"Evaluation failed: {str(e)}"
    else:
        success = False
    
    # 打印结果
    print('Evaluation Results:')
    if process:
        for key, value in result_dict.items():
            print(f'{key}: {value}')
    else:
        print(f'Error: {comments}')
    
    # 保存结果到 JSONL（如果提供了 --result）
    if args.result:
        save_result_to_jsonl(args.result, process, success, comments)

if __name__ == '__main__':
    main()