import argparse
import numpy as np
from PIL import Image
import json
import os
from datetime import datetime
from scipy.ndimage import sobel


def compute_edge_intensity(img_array):
    """
    Calculate image edge intensity (Sobel gradient).

    Args:
        img_array (np.ndarray): Input image (RGB or grayscale)

    Returns:
        np.ndarray: Edge intensity map
    """
    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = np.mean(img_array, axis=2).astype(np.float32)
    else:
        gray = img_array.astype(np.float32)

    # Calculate Sobel gradient
    grad_x = sobel(gray, axis=1)
    grad_y = sobel(gray, axis=0)
    edge_intensity = np.sqrt(grad_x ** 2 + grad_y ** 2)
    return edge_intensity


def evaluate_blur_background(input_path, output_path):
    """
    Evaluate blur background replacement quality without pretrained model.

    Args:
        input_path (str): Input image path
        output_path (str): Output image path (with blurred background)

    Returns:
        dict: Evaluation results containing BBI, FSP and success status
    """
    # Load images
    input_img = Image.open(input_path).convert('RGB')
    output_img = Image.open(output_path).convert('RGB')

    # Convert to numpy arrays
    input_array = np.array(input_img)
    output_array = np.array(output_img)

    # Calculate edge intensity of output image
    edge_intensity = compute_edge_intensity(output_array)

    # Segment background and foreground (based on edge intensity)
    edge_threshold = np.percentile(edge_intensity, 50)  # Median as threshold
    background_mask = edge_intensity <= edge_threshold  # Low edge intensity = background
    foreground_mask = edge_intensity > edge_threshold  # High edge intensity = foreground

    # Save masks for debugging
    background_mask_img = Image.fromarray(background_mask.astype(np.uint8) * 255)
    foreground_mask_img = Image.fromarray(foreground_mask.astype(np.uint8) * 255)

    # Metric 1: Background Blur Intensity (BBI)
    # Calculate average edge intensity of background region (lower = more blurred)
    background_edges = edge_intensity[background_mask]
    bbi = np.mean(background_edges) if background_edges.size > 0 else float('inf')

    # Metric 2: Foreground Sharpness Preservation (FSP)
    # Compare edge intensity difference between input and output foreground regions
    input_edge_intensity = compute_edge_intensity(input_array)
    input_foreground_edges = input_edge_intensity[foreground_mask]
    output_foreground_edges = edge_intensity[foreground_mask]

    if input_foreground_edges.size == 0 or output_foreground_edges.size == 0:
        fsp = float('inf')  # No foreground pixels, task failed
    else:
        input_mean_edge = np.mean(input_foreground_edges)
        output_mean_edge = np.mean(output_foreground_edges)
        fsp = abs(input_mean_edge - output_mean_edge) / (input_mean_edge + 1e-10)  # Relative difference

    # Determine if task succeeded
    bbi_threshold = 20  # Background edge intensity threshold (lower = more blurred)
    fsp_threshold = 0.2  # Foreground sharpness change threshold
    success = bbi <= bbi_threshold and fsp <= fsp_threshold

    # Return results
    return {
        'BBI (Background Blur Intensity)': bbi,
        'BBI Threshold': bbi_threshold,
        'FSP (Foreground Sharpness Preservation)': fsp,
        'FSP Threshold': fsp_threshold,
        'Success': success
    }


def validate_inputs(input_path, output_path):
    """
    Validate input files exist, are non-empty, and have correct format.

    Returns:
        tuple: (bool, str) - (is valid, error message or empty string)
    """
    try:
        # Check if files exist
        if not os.path.exists(input_path):
            return False, f"Input file {input_path} does not exist."
        if not os.path.exists(output_path):
            return False, f"Output file {output_path} does not exist."

        # Check if files are non-empty
        if os.path.getsize(input_path) == 0:
            return False, f"Input file {input_path} is empty."
        if os.path.getsize(output_path) == 0:
            return False, f"Output file {output_path} is empty."

        # Check file format (try opening images)
        try:
            with Image.open(input_path) as img:
                img.verify()  # Verify image format
            with Image.open(output_path) as img:
                img.verify()
        except Exception as e:
            return False, f"Invalid image format: {str(e)}"

        return True, ""
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def save_result_to_jsonl(result_path, process, result, comments):
    """
    Save results to JSONL file.

    Args:
        result_path (str): JSONL file path
        process (bool): Whether input parameters are valid
        result (bool): Whether evaluation succeeded
        comments (str): Remarks
    """
    # Generate timestamp
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    record = {
        "Process": bool(process),  # Ensure boolean
        "Result": bool(result),  # Ensure boolean
        "TimePoint": time_point,
        "comments": comments
    }

    # Append to JSONL file
    try:
        with open(result_path, 'a', encoding='utf-8') as f:
            json_line = json.dumps(record, ensure_ascii=False, default=str)
            f.write(json_line + '\n')
    except Exception as e:
        print(f"Failed to save result to {result_path}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate blur background replacement quality without pretrained model.')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to input image')
    parser.add_argument('--output', type=str, required=True, help='Path to output image (blur background)')
    parser.add_argument('--result', type=str, help='Path to JSONL file to save results')

    args = parser.parse_args()

    # Validate input parameters
    process, comments = validate_inputs(args.groundtruth, args.output)

    # Initialize results
    result_dict = {}
    success = False

    # If inputs are valid, run evaluation
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

    # Print results
    print('Evaluation Results:')
    if process:
        for key, value in result_dict.items():
            print(f'{key}: {value}')
    else:
        print(f'Error: {comments}')

    # Save results to JSONL (if --result provided)
    if args.result:
        save_result_to_jsonl(args.result, process, success, comments)


if __name__ == '__main__':
    main()