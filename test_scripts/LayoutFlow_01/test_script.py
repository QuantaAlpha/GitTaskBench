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


# For serializing Tensors to JSON
class TensorEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, torch.Tensor):
            return obj.tolist()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(TensorEncoder, self).default(obj)


# Convert from center format (x, y, w, h) to corner format (l, t, r, b)
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
        # Handle special cases
        xc, yc, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        x1 = xc - w / 2
        y1 = yc - h / 2
        x2 = xc + w / 2
        y2 = yc + h / 2
        return torch.stack([x1, y1, x2, y2])


# Calculate layout alignment score
def compute_alignment(bbox, mask, format='xywh', output_torch=False):
    """Calculate layout alignment score

    Args:
        bbox: [B, N, 4] tensor containing layout bounding box coordinates
        mask: [B, N] boolean tensor indicating valid elements
        format: coordinate format, 'xywh' for center coordinates, 'ltrb' for corner coordinates
        output_torch: whether to return torch tensor

    Returns:
        Alignment score (lower values indicate better alignment)
    """
    bbox = bbox.permute(2, 0, 1)  # [4, B, N]
    if format == 'xywh':
        # Convert to corner coordinates
        xl, yt, xr, yb = convert_xywh_to_ltrb(bbox.permute(1, 2, 0)).permute(2, 0, 1)
    elif format == 'ltrb':
        xl, yt, xr, yb = bbox
    else:
        print(f'Format {format} not supported.')
        return None

    # Calculate center coordinates
    xc = (xr + xl) / 2
    yc = (yt + yb) / 2

    # Collect all reference lines (left/center/right, top/center/bottom)
    X = torch.stack([xl, xc, xr, yt, yc, yb], dim=1)  # [B, 6, N]

    # Calculate distance from each element to all reference lines of other elements
    X = X.unsqueeze(-1) - X.unsqueeze(-2)  # [B, 6, N, N]

    # Set distance to self as 1 (ignore)
    idx = torch.arange(X.size(2), device=X.device)
    X[:, :, idx, idx] = 1.

    # Calculate absolute distance and rearrange dimensions
    X = X.abs().permute(0, 2, 1, 3)  # [B, N, 6, N]

    # Set distance for invalid elements to 1 (ignore)
    X[~mask] = 1.

    # For each element, find the minimum distance to closest reference line of other elements
    X = X.min(-1).values.min(-1).values  # [B, N]

    # Remove distances equal to 1 (self-to-self or invalid elements)
    X.masked_fill_(X.eq(1.), 0.)

    # Transform distance to alignment score: -log(1-d), smaller distance = smaller score
    X = -torch.log(1 - X)

    # Calculate average alignment score
    if not output_torch:
        score = torch.from_numpy(np.nan_to_num((X.sum(-1) / mask.float().sum(-1)))).numpy()
    else:
        score = torch.nan_to_num(X.sum(-1) / mask.float().sum(-1))

    return score.mean().item()


# Load layout data from JSON file
def load_layout_data(file_path):
    """Load layout data from JSON file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Convert lists to tensors
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
        print(f"Error loading file {file_path}: {e}")
        return None


# Calculate overlap ratio
def compute_overlap(bbox, mask, format='xywh'):
    """Calculate overlap ratio between layout elements

    Args:
        bbox: [B, N, 4] tensor containing layout bounding box coordinates
        mask: [B, N] boolean tensor indicating valid elements
        format: coordinate format, 'xywh' for center coordinates, 'ltrb' for corner coordinates

    Returns:
        Overlap ratio score (lower values indicate less overlap)
    """
    # Set coordinates of invalid elements to 0
    bbox = bbox.masked_fill(~mask.unsqueeze(-1), 0)
    bbox = bbox.permute(2, 0, 1)  # [4, B, N]

    if format == 'xywh':
        # Convert to corner coordinates
        l1, t1, r1, b1 = convert_xywh_to_ltrb(bbox.unsqueeze(-1))
        l2, t2, r2, b2 = convert_xywh_to_ltrb(bbox.unsqueeze(-2))
    elif format == 'ltrb':
        l1, t1, r1, b1 = bbox.unsqueeze(-1)
        l2, t2, r2, b2 = bbox.unsqueeze(-2)
    else:
        print(f'Format {format} not supported.')
        return None

    # Calculate area of each box
    a1 = (r1 - l1) * (b1 - t1)  # [4, B, N, 1]

    # Calculate intersection
    l_max = torch.maximum(l1, l2)
    r_min = torch.minimum(r1, r2)
    t_max = torch.maximum(t1, t2)
    b_min = torch.minimum(b1, b2)
    cond = (l_max < r_min) & (t_max < b_min)
    ai = torch.where(cond, (r_min - l_max) * (b_min - t_max),
                     torch.zeros_like(a1[0]))  # [B, N, N]

    # Ignore self-overlap
    diag_mask = torch.eye(a1.size(1), dtype=torch.bool,
                          device=a1.device)
    ai = ai.masked_fill(diag_mask, 0)

    # Calculate ratio of intersection to first box area
    ar = ai / a1
    ar = torch.from_numpy(np.nan_to_num(ar.numpy()))

    # Calculate average overlap ratio
    score = torch.from_numpy(
        np.nan_to_num((ar.sum(dim=(1, 2)) / mask.float().sum(-1)).numpy())
    )
    return score.mean().item()


def evaluate_layout(input_file):
    """Evaluate layout quality

    Args:
        input_file: Path to input JSON file

    Returns:
        Dictionary containing evaluation results
    """
    process_status = True
    final_result_status = False
    comments = []

    # Timestamp
    time_point = datetime.now().isoformat()

    # Check input file
    if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
        comments.append(f"Error: Layout file '{input_file}' does not exist or is empty.")
        process_status = False

    if process_status:
        try:
            # Load layout data
            layouts = load_layout_data(input_file)
            if layouts is None:
                comments.append(f"Error: Failed to load layout data.")
                process_status = False
            else:
                # Calculate alignment score
                alignment_score = compute_alignment(layouts['bbox'], layouts['pad_mask'])

                # Calculate overlap ratio
                overlap_score = compute_overlap(layouts['bbox'], layouts['pad_mask'])

                # Collect statistics
                num_layouts = layouts['bbox'].shape[0]

                # Calculate number of elements per layout
                element_counts = layouts['pad_mask'].sum(dim=1).tolist()
                avg_elements = sum(element_counts) / len(element_counts)

                # Calculate class distribution
                valid_labels = []
                for i in range(layouts['label'].shape[0]):
                    mask = layouts['pad_mask'][i]
                    valid_labels.extend(layouts['label'][i][mask].tolist())

                label_counts = {}
                for l in valid_labels:
                    label_counts[int(l)] = label_counts.get(int(l), 0) + 1

                # Evaluation criteria
                alignment_satisfied = alignment_score < 2.0  # Alignment score threshold (example)
                overlap_satisfied = overlap_score < 0.1  # Overlap ratio threshold (example)

                comments.append(f"📊 Number of layouts: {num_layouts}")
                comments.append(f"📏 Alignment score: {alignment_score:.4f} (lower is better)")
                comments.append(f"🔍 Overlap ratio: {overlap_score:.4f} (lower is better)")
                comments.append(f"📈 Average elements per layout: {avg_elements:.2f}")
                comments.append(f"🎯 Alignment < 2.0: {'✅ Satisfied' if alignment_satisfied else '❌ Not satisfied'}")
                comments.append(f"🎯 Overlap < 0.1: {'✅ Satisfied' if overlap_satisfied else '❌ Not satisfied'}")

                final_result_status = alignment_satisfied and overlap_satisfied
                comments.append(
                    f"Final evaluation: Alignment satisfied={alignment_satisfied}, Overlap satisfied={overlap_satisfied}")

                # Detailed metrics
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
            comments.append(f"Exception during layout evaluation: {e}")
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
    Append single result to JSONL file:
    Each execution adds one JSON line.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            # Use default=str to handle non-serializable types
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
        print(f"✅ Results appended to JSONL file: {file_path}")
    except Exception as e:
        print(f"❌ Error writing to JSONL file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate layout quality and generate report')
    parser.add_argument('--output', required=True, help='Path to input layout JSON file')
    parser.add_argument('--result', help='Path to store JSONL results file')

    args = parser.parse_args()

    print(f"Starting layout evaluation for {args.output}")

    # Evaluate layout
    evaluation_result = evaluate_layout(args.output)

    # Output results
    if args.result:
        write_to_jsonl(args.result, evaluation_result)

    print("\nEvaluation completed")