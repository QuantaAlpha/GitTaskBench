#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import torch
import numpy as np
import json
import argparse
from typing import Dict, List, Optional, Tuple, Union
import sys
from datetime import datetime

# 用于序列化Tensor到JSON
class TensorEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, torch.Tensor):
            return obj.tolist()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(TensorEncoder, self).default(obj)

# 从中心点坐标转换为左上右下坐标
def convert_xywh_to_ltrb(bbox):
    """Convert from center format (x, y, w, h) to corner format (l, t, r, b)"""
    if isinstance(bbox, np.ndarray):
        lib = np
    else:
        lib = torch
    
    if bbox.dim() == 2:  # [N, 4]
        xc, yc, w, h = bbox[:, 0], bbox[:, 1], bbox[:, 2], bbox[:, 3]
        x1 = xc - w / 2
        y1 = yc - h / 2
        x2 = xc + w / 2
        y2 = yc + h / 2
        return torch.stack([x1, y1, x2, y2], dim=1)
    elif bbox.dim() == 3:  # [B, N, 4]
        xc, yc, w, h = bbox[:, :, 0], bbox[:, :, 1], bbox[:, :, 2], bbox[:, :, 3]
        x1 = xc - w / 2
        y1 = yc - h / 2
        x2 = xc + w / 2
        y2 = yc + h / 2
        return torch.stack([x1, y1, x2, y2], dim=2)
    else:
        # 处理特殊情况
        xc, yc, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        x1 = xc - w / 2
        y1 = yc - h / 2
        x2 = xc + w / 2
        y2 = yc + h / 2
        return torch.stack([x1, y1, x2, y2])

# 计算布局的对齐度
def compute_alignment(bbox, mask, format='xywh', output_torch=False):
    """计算布局的对齐度
    
    参数:
        bbox: [B, N, 4] 的张量，包含布局的边界框坐标
        mask: [B, N] 的布尔张量，表示有效元素
        format: 坐标格式，'xywh'表示中心点坐标，'ltrb'表示左上右下坐标
        output_torch: 是否返回torch张量
        
    返回:
        对齐度分数 (值越小表示对齐度越好)
    """
    bbox = bbox.permute(2, 0, 1)  # [4, B, N]
    if format == 'xywh':
        # 转换为左上右下坐标
        xl, yt, xr, yb = convert_xywh_to_ltrb(bbox.permute(1, 2, 0)).permute(2, 0, 1)
    elif format == 'ltrb':
        xl, yt, xr, yb = bbox
    else:
        print(f'{format}格式不支持.')
        return None
    
    # 计算中心点坐标
    xc = (xr + xl) / 2
    yc = (yt + yb) / 2
    
    # 收集所有参考线（左/中/右，上/中/下）
    X = torch.stack([xl, xc, xr, yt, yc, yb], dim=1)  # [B, 6, N]
    
    # 计算每个元素到其他所有元素所有参考线的距离
    X = X.unsqueeze(-1) - X.unsqueeze(-2)  # [B, 6, N, N]
    
    # 将自己与自己的距离设置为1（不考虑）
    idx = torch.arange(X.size(2), device=X.device)
    X[:, :, idx, idx] = 1.
    
    # 计算距离的绝对值，并重新排列维度
    X = X.abs().permute(0, 2, 1, 3)  # [B, N, 6, N]
    
    # 无效元素的距离设为1（不考虑）
    X[~mask] = 1.
    
    # 对于每个元素，找到最接近其他元素的参考线的最小距离
    X = X.min(-1).values.min(-1).values  # [B, N]
    
    # 移除距离为1的值（自己到自己的距离或无效元素）
    X.masked_fill_(X.eq(1.), 0.)
    
    # 变换距离为对齐分数：-log(1-d)，距离越小，分数越小
    X = -torch.log(1 - X)
    
    # 计算平均对齐分数
    if not output_torch:
        score = torch.from_numpy(np.nan_to_num((X.sum(-1) / mask.float().sum(-1)))).numpy()
    else:
        score = torch.nan_to_num(X.sum(-1) / mask.float().sum(-1))
    
    return score.mean().item()

# 从JSON文件加载布局数据
def load_layout_data(file_path):
    """从JSON文件加载布局数据"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # 将列表转换为tensor
        if 'bbox' in data:
            data['bbox'] = torch.tensor(data['bbox'])
        if 'ltrb_bbox' in data:
            data['ltrb_bbox'] = torch.tensor(data['ltrb_bbox'])
        if 'label' in data:
            data['label'] = torch.tensor(data['label'])
        if 'pad_mask' in data:
            data['pad_mask'] = torch.tensor(data['pad_mask'], dtype=torch.bool)
        
        return data
    except Exception as e:
        print(f"加载文件 {file_path} 时出错: {e}")
        return None

# 计算重叠率
def compute_overlap(bbox, mask, format='xywh'):
    """计算布局元素之间的重叠率
    
    参数:
        bbox: [B, N, 4] 的张量，包含布局的边界框坐标
        mask: [B, N] 的布尔张量，表示有效元素
        format: 坐标格式，'xywh'表示中心点坐标，'ltrb'表示左上右下坐标
        
    返回:
        重叠率分数 (值越小表示重叠越少)
    """
    # 将无效元素的坐标置为0
    bbox = bbox.masked_fill(~mask.unsqueeze(-1), 0)
    bbox = bbox.permute(2, 0, 1)  # [4, B, N]

    if format == 'xywh':
        # 转换为左上右下坐标
        l1, t1, r1, b1 = convert_xywh_to_ltrb(bbox.unsqueeze(-1))
        l2, t2, r2, b2 = convert_xywh_to_ltrb(bbox.unsqueeze(-2))
    elif format == 'ltrb':
        l1, t1, r1, b1 = bbox.unsqueeze(-1)
        l2, t2, r2, b2 = bbox.unsqueeze(-2)
    else:
        print(f'{format}格式不支持.')
        return None

    # 计算每个框的面积
    a1 = (r1 - l1) * (b1 - t1)  # [4, B, N, 1]

    # 计算交集
    l_max = torch.maximum(l1, l2)
    r_min = torch.minimum(r1, r2)
    t_max = torch.maximum(t1, t2)
    b_min = torch.minimum(b1, b2)
    cond = (l_max < r_min) & (t_max < b_min)
    ai = torch.where(cond, (r_min - l_max) * (b_min - t_max),
                     torch.zeros_like(a1[0]))  # [B, N, N]

    # 不考虑自己与自己的重叠
    diag_mask = torch.eye(a1.size(1), dtype=torch.bool,
                        device=a1.device)
    ai = ai.masked_fill(diag_mask, 0)

    # 计算交集与第一个框面积的比率
    ar = ai / a1
    ar = torch.from_numpy(np.nan_to_num(ar.numpy()))
    
    # 计算平均重叠率
    score = torch.from_numpy(
        np.nan_to_num((ar.sum(dim=(1, 2)) / mask.float().sum(-1)).numpy())
    )
    return score.mean().item()

def evaluate_layout(input_file):
    """评估布局质量
    
    参数:
        input_file: 输入JSON文件路径
    
    返回:
        包含评估结果的字典
    """
    process_status = True
    final_result_status = False
    comments = []
    
    # 时间戳
    time_point = datetime.now().isoformat()
    
    # 检查输入文件
    if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
        comments.append(f"错误：布局文件 '{input_file}' 不存在或为空。")
        process_status = False
    
    if process_status:
        try:
            # 加载布局数据
            layouts = load_layout_data(input_file)
            if layouts is None:
                comments.append(f"错误：加载布局数据失败。")
                process_status = False
            else:
                # 计算对齐度
                alignment_score = compute_alignment(layouts['bbox'], layouts['pad_mask'])
                
                # 计算重叠率
                overlap_score = compute_overlap(layouts['bbox'], layouts['pad_mask'])
                
                # 收集统计信息
                num_layouts = layouts['bbox'].shape[0]
                
                # 计算每个布局的元素数量
                element_counts = layouts['pad_mask'].sum(dim=1).tolist()
                avg_elements = sum(element_counts) / len(element_counts)
                
                # 计算类别分布
                valid_labels = []
                for i in range(layouts['label'].shape[0]):
                    mask = layouts['pad_mask'][i]
                    valid_labels.extend(layouts['label'][i][mask].tolist())
                
                label_counts = {}
                for l in valid_labels:
                    label_counts[int(l)] = label_counts.get(int(l), 0) + 1
                
                # 评估标准
                alignment_satisfied = alignment_score < 2.0 # 对齐度分数阈值（示例）
                overlap_satisfied = overlap_score < 0.1    # 重叠率分数阈值（示例）
                
                comments.append(f"📊 布局数量: {num_layouts}")
                comments.append(f"📏 对齐度分数: {alignment_score:.4f} (越小越好)")
                comments.append(f"🔍 重叠率分数: {overlap_score:.4f} (越小越好)")
                comments.append(f"📈 平均元素数量: {avg_elements:.2f}")
                comments.append(f"🎯 对齐度 < 2.0: {'✅ 满足' if alignment_satisfied else '❌ 不满足'}")
                comments.append(f"🎯 重叠率 < 0.1: {'✅ 满足' if overlap_satisfied else '❌ 不满足'}")
                
                final_result_status = alignment_satisfied and overlap_satisfied
                comments.append(f"最终评估结果：对齐度满足={alignment_satisfied}, 重叠率满足={overlap_satisfied}")
                
                # 详细指标结果
                evaluation_details = {
                    "num_layouts": num_layouts,
                    "alignment_score": alignment_score,
                    "overlap_score": overlap_score,
                    "avg_elements_per_layout": avg_elements,
                    "max_elements": max(element_counts),
                    "min_elements": min(element_counts),
                    "label_distribution": label_counts
                }
                
        except Exception as e:
            comments.append(f"布局评估过程中发生异常: {e}")
            process_status = False
            final_result_status = False
    
    output_data = {
        "Process": process_status,
        "Result": final_result_status,
        "TimePoint": time_point,
        "Comments": "\n".join(comments)
    }
    
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
    parser = argparse.ArgumentParser(description='评估布局质量并生成报告')
    parser.add_argument('--output', required=True, help='输入的布局JSON文件路径')
    parser.add_argument('--result', help='用于存储 JSONL 结果的文件路径')
    
    args = parser.parse_args()
    
    print(f"开始评估布局 {args.output}")
    
    # 评估布局
    evaluation_result = evaluate_layout(args.output)
    
    # 输出结果
    if args.result:
        write_to_jsonl(args.result, evaluation_result)
    
    print("\n评估完成") 