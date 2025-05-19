import argparse
import numpy as np
from PIL import Image
import json
import os
from datetime import datetime

def detect_dominant_green(output_array):
    """
    检测输出图像中最常见的绿色变体作为绿幕颜色。

    参数:
        output_array (np.ndarray): 输出图像的 RGB 数组

    返回:
        np.ndarray: 检测到的绿幕颜色（RGB）
    """
    # 过滤绿色像素（绿色通道值显著高于红色和蓝色）
    green_candidates = output_array[
        (output_array[:, :, 1] > output_array[:, :, 0] + 50) & 
        (output_array[:, :, 1] > output_array[:, :, 2] + 50)
    ]
    
    if green_candidates.size == 0:
        # 如果没有明显的绿色像素，回退到默认绿色
        return np.array([0, 255, 0])
    
    # 计算绿色像素的平均颜色
    dominant_green = np.mean(green_candidates, axis=0).astype(int)
    return dominant_green

def evaluate_green_background(input_path, output_path):
    """
    评估绿幕背景替换任务的完成质量，无需预训练模型，动态检测绿幕颜色。

    参数:
        input_path (str): 输入图像路径
        output_path (str): 输出图像路径（绿幕背景）

    返回:
        dict: 包含 BGC、FCF 和是否成功的评估结果
    """
    # 加载图像
    input_img = Image.open(input_path).convert('RGB')
    output_img = Image.open(output_path).convert('RGB')
    
    # 转换为 numpy 数组
    input_array = np.array(input_img)
    output_array = np.array(output_img)
    
    # 动态检测绿幕颜色
    green_color = detect_dominant_green(output_array)
    green_threshold = 70  # 放宽阈值以适应绿色变体

    # 指标 1：背景绿色覆盖率 (BGC)
    # 计算输出图像中接近绿幕颜色的像素比例
    color_diff = np.sqrt(np.sum((output_array - green_color) ** 2, axis=2))
    green_mask = color_diff <= green_threshold
    bgc = np.mean(green_mask)  # 绿色像素比例

    # 保存绿色掩码用于调试
    green_mask_img = Image.fromarray(green_mask.astype(np.uint8) * 255)


    # 指标 2：前景颜色保持度 (FCF)
    # 提取非绿色像素（假设为前景）
    non_green_mask = color_diff > green_threshold
    input_non_green = input_array[non_green_mask]
    output_non_green = output_array[non_green_mask]
    
    # 保存非绿色掩码用于调试
    non_green_mask_img = Image.fromarray(non_green_mask.astype(np.uint8) * 255)

    
    if input_non_green.size == 0 or output_non_green.size == 0:
        fcf = float('inf')  # 无非绿色像素，任务失败
    else:
        # 计算非绿色像素的平均颜色偏差
        color_diff_non_green = np.mean(np.abs(input_non_green - output_non_green))
        fcf = color_diff_non_green
    
    # 判断任务是否成功
    bgc_threshold = 0.4  # 绿色覆盖率阈值
    fcf_threshold = 200  # 前景颜色偏差阈值
    success = bgc >= bgc_threshold and fcf <= fcf_threshold
    
    # 返回结果
    return {
        'BGC (Background Green Coverage)': bgc,
        'BGC Threshold': bgc_threshold,
        'FCF (Foreground Color Fidelity)': fcf,
        'FCF Threshold': fcf_threshold,
        'Success': success,
        'Detected Green Color': green_color.tolist()  # 记录检测到的绿幕颜色
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
    
    # 构建 JSONL 记录
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
    parser = argparse.ArgumentParser(description='Evaluate green background replacement quality without pretrained model.')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to input image')
    parser.add_argument('--output', type=str, required=True, help='Path to output image (green background)')
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
            result_dict = evaluate_green_background(args.groundtruth, args.output)
            success = result_dict['Success']
            comments = (
                f"BGC: {result_dict['BGC (Background Green Coverage)']:.3f} "
                f"(Threshold: {result_dict['BGC Threshold']}), "
                f"FCF: {result_dict['FCF (Foreground Color Fidelity)']:.3f} "
                f"(Threshold: {result_dict['FCF Threshold']}), "
                f"Detected Green Color: {result_dict['Detected Green Color']}, "
                f"Success: {success}"
            )
            if not success:
                comments += ". Possible issues: BGC too low (insufficient green background) or FCF too high (foreground color distortion)."
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