#!/usr/bin/env python3
import argparse
import os
import json
import datetime
import numpy as np
from PIL import Image, UnidentifiedImageError
import cv2


def main():
    parser = argparse.ArgumentParser(description='Automated scratch detection test script')
    parser.add_argument(
        '--output',
        required=True,
        help='Path to output image for detection'
    )
    parser.add_argument(
        '--result',
        required=True,
        help='Path to result JSONL file (created if not exists, appended if exists)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.05,
        help='Scratch detection threshold, default 0.05'
    )
    parser.add_argument(
        '--min-length',
        type=int,
        default=50,
        help='Minimum scratch length, default 50 pixels'
    )
    args = parser.parse_args()
    process = False
    result = False
    comments = []
    # —— Step 1: Validate input file ——
    if not os.path.isfile(args.output):
        comments.append(f'File not found: {args.output}')
    elif os.path.getsize(args.output) == 0:
        comments.append(f'File is empty: {args.output}')
    else:
        try:
            # Verify format
            img = Image.open(args.output)
            img.verify()
            process = True
            # Reopen to read pixels
            img = Image.open(args.output)
            # Convert to numpy array
            img_array = np.array(img)

            # —— Step 2: Scratch detection logic ——
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray_img = img_array

            # Apply Gaussian blur to remove noise
            blurred = cv2.GaussianBlur(gray_img, (5, 5), 0)

            # Use Canny edge detection
            edges = cv2.Canny(blurred, 50, 150)

            # Use Hough transform to detect lines
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                    threshold=50,
                                    minLineLength=args.min_length,
                                    maxLineGap=10)

            # Calculate scratch features
            if lines is not None:
                scratch_count = len(lines)
                # Calculate cumulative length and average intensity
                total_length = 0
                line_intensities = []

                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    total_length += length

                    # Calculate average intensity along the line
                    line_points = np.linspace((x1, y1), (x2, y2), int(length), dtype=np.int32)
                    points_intensity = []
                    for x, y in line_points:
                        if 0 <= x < gray_img.shape[1] and 0 <= y < gray_img.shape[0]:
                            points_intensity.append(gray_img[y, x])

                    if points_intensity:
                        line_intensities.append(np.mean(points_intensity))

                # Calculate features
                avg_intensity = np.mean(line_intensities) if line_intensities else 0
                intensity_std = np.std(line_intensities) if line_intensities else 0
                avg_length = total_length / scratch_count if scratch_count > 0 else 0

                # Scratch score - combines line count, length and intensity variation
                scratch_score = (scratch_count * avg_length * intensity_std) / (img_array.size * 255)

                if scratch_score > args.threshold:
                    comments.append(
                        f'Potential scratches detected: {scratch_count} lines, avg length {avg_length:.2f}px, intensity variation {intensity_std:.2f}, score {scratch_score:.6f}, exceeds threshold {args.threshold}')
                    result = False
                else:
                    comments.append(f'No significant scratches detected: score {scratch_score:.6f}, below threshold {args.threshold}')
                    result = True
            else:
                comments.append('No lines detected, no scratches found')
                result = True

        except UnidentifiedImageError as e:
            comments.append(f'Invalid image format: {e}')
        except Exception as e:
            comments.append(f'Error reading image: {e}')
    print("; ".join(comments))
    # —— Step 3: Write to JSONL ——
    entry = {
        "Process": process,
        "Result": result,
        "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
        "comments": "; ".join(comments)
    }
    # Append mode, one entry per line
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


if __name__ == "__main__":
    main()