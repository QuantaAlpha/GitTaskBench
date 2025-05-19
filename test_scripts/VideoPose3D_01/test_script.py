#!/usr/bin/env python3
import os
import argparse
import numpy as np
import json
import datetime

def parse_args():
    parser = argparse.ArgumentParser(description='VideoPose3D输出评估')
    parser.add_argument('--output', type=str, default='output/VideoPose3D_01/output_3d.npz.npy',
                        help='输入3D关键点文件路径')
    parser.add_argument('--result', type=str, default='test_results/VideoPose3D_01/results.jsonl',
                        help='评估结果的jsonl文件路径')
    return parser.parse_args()

def load_data(file_path):
    try:
        data = np.load(file_path, allow_pickle=True)
        return data
    except Exception as e:
        print(f"加载数据出错: {e}")
        return None

def evaluate_data(data):
    results = {}
    shape = data.shape
    results['shape'] = shape
    results['dtype'] = str(data.dtype)
    results['has_nan'] = np.isnan(data).any()
    results['min'] = float(np.min(data))
    results['max'] = float(np.max(data))
    results['mean'] = float(np.mean(data))
    results['std'] = float(np.std(data))
    frame_diffs = np.sqrt(np.sum(np.square(data[1:] - data[:-1]), axis=(1, 2))) if data.shape[0] > 1 else np.array([])
    results['avg_frame_diff'] = float(np.mean(frame_diffs)) if frame_diffs.size > 0 else 0.0
    results['max_frame_diff'] = float(np.max(frame_diffs)) if frame_diffs.size > 0 else 0.0
    limbs = [
        (0, 1), (1, 2), (2, 3), (1, 4), (4, 5),
        (0, 6), (6, 7), (7, 8), (8, 9), (7, 10), (10, 11)
    ]
    bone_lengths = []
    for joint1, joint2 in limbs:
        if joint1 < data.shape[1] and joint2 < data.shape[1]:
            bone_vec = data[:, joint1, :] - data[:, joint2, :]
            lengths = np.sqrt(np.sum(np.square(bone_vec), axis=1))
            cv = np.std(lengths) / np.mean(lengths) if np.mean(lengths) != 0 else 0
            bone_lengths.append((joint1, joint2, float(cv)))
    results['bone_length_stability'] = bone_lengths
    score = 100.0
    if results['has_nan']:
        score -= 20
    avg_cv = np.mean([cv for _, _, cv in bone_lengths])
    if avg_cv > 0.1:
        score -= min(30, avg_cv * 100)
    if results['max_frame_diff'] > 1.0:
        score -= min(20, results['max_frame_diff'] * 10)
    results['score'] = max(0, score)
    return results

def save_results_to_jsonl(process_status, test_passed, comments, result_file):
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result_data = {
        "Process": process_status,
        "Result": test_passed,
        "TimePoint": current_time,
        "comments": comments
    }
    with open(result_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result_data, ensure_ascii=False, default=str) + '\n')
    print(f"评估结果已写入: {result_file}")

def main():
    args = parse_args()
    if not os.path.exists(args.output):
        print(f"错误: 输入文件 {args.output} 不存在")
        comments = f"错误: 输入文件 {args.output} 不存在"
        save_results_to_jsonl(False, False, comments, args.result)
        return  # 不退出，只返回
    data = load_data(args.output)
    if data is None:
        comments = f"错误: 无法加载输入文件 {args.output}"
        save_results_to_jsonl(False, False, comments, args.result)
        return
    if isinstance(data, np.lib.npyio.NpzFile):
        if len(data.files) == 0:
            comments = f"错误: 输入文件 {args.output} 中没有任何数组"
            save_results_to_jsonl(False, False, comments, args.result)
            return
        first_key = data.files[0]
        data = data[first_key]
    if len(data.shape) == 4 and data.shape[0] == 1 and data.shape[1] == 1 and data.shape[3] == 3:
        data = data[0, 0]
        data = data[np.newaxis, ...]
    if len(data.shape) != 3 or data.shape[2] != 3:
        comments = f"错误: 输入文件格式不正确，预期形状为(frames, joints, 3)，但实际为{data.shape}"
        save_results_to_jsonl(False, False, comments, args.result)
        return
    print(f"数据形状: {data.shape}")
    results = evaluate_data(data)
    print(f"评估完成! 总体评分: {results['score']:.2f}/100")
    test_passed = results['score'] >= 60
    comments = f"评估完成! 总体评分: {results['score']:.2f}/100。"
    if test_passed:
        comments += "结果: 通过 ✅"
        print("结果: 通过 ✅")
    else:
        comments += "结果: 不通过 ❌"
        print("结果: 不通过 ❌")
    save_results_to_jsonl(True, test_passed, comments, args.result)

if __name__ == "__main__":
    main()  
