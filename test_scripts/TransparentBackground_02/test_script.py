import argparse
import numpy as np
from PIL import Image
import json
import os
from datetime import datetime


def detect_dominant_green(output_array):
    """
    Detect the most common green variant as the green screen color.

    Args:
        output_array (np.ndarray): Output image RGB array

    Returns:
        np.ndarray: Detected green screen color (RGB)
    """
    # Filter green pixels (green channel significantly higher than red and blue)
    green_candidates = output_array[
        (output_array[:, :, 1] > output_array[:, :, 0] + 50) &
        (output_array[:, :, 1] > output_array[:, :, 2] + 50)
        ]

    if green_candidates.size == 0:
        # Fallback to default green if no obvious green pixels found
        return np.array([0, 255, 0])

    # Calculate average color of green pixels
    dominant_green = np.mean(green_candidates, axis=0).astype(int)
    return dominant_green


def evaluate_green_background(input_path, output_path):
    """
    Evaluate green screen background replacement quality without pretrained model, dynamically detecting green screen color.

    Args:
        input_path (str): Input image path
        output_path (str): Output image path (with green background)

    Returns:
        dict: Evaluation results containing BGC, FCF and success status
    """
    # Load images
    input_img = Image.open(input_path).convert('RGB')
    output_img = Image.open(output_path).convert('RGB')

    # Convert to numpy arrays
    input_array = np.array(input_img)
    output_array = np.array(output_img)

    # Dynamically detect green screen color
    green_color = detect_dominant_green(output_array)
    green_threshold = 70  # Relaxed threshold to accommodate green variants

    # Metric 1: Background Green Coverage (BGC)
    # Calculate proportion of pixels close to green screen color
    color_diff = np.sqrt(np.sum((output_array - green_color) ** 2, axis=2))
    green_mask = color_diff <= green_threshold
    bgc = np.mean(green_mask)  # Green pixel proportion

    # Save green mask for debugging
    green_mask_img = Image.fromarray(green_mask.astype(np.uint8) * 255)

    # Metric 2: Foreground Color Fidelity (FCF)
    # Extract non-green pixels (assumed to be foreground)
    non_green_mask = color_diff > green_threshold
    input_non_green = input_array[non_green_mask]
    output_non_green = output_array[non_green_mask]

    # Save non-green mask for debugging
    non_green_mask_img = Image.fromarray(non_green_mask.astype(np.uint8) * 255)

    if input_non_green.size == 0 or output_non_green.size == 0:
        fcf = float('inf')  # No non-green pixels, task failed
    else:
        # Calculate average color difference of non-green pixels
        color_diff_non_green = np.mean(np.abs(input_non_green - output_non_green))
        fcf = color_diff_non_green

    # Determine if task succeeded
    bgc_threshold = 0.4  # Green coverage threshold
    fcf_threshold = 200  # Foreground color difference threshold
    success = bgc >= bgc_threshold and fcf <= fcf_threshold

    # Return results
    return {
        'BGC (Background Green Coverage)': bgc,
        'BGC Threshold': bgc_threshold,
        'FCF (Foreground Color Fidelity)': fcf,
        'FCF Threshold': fcf_threshold,
        'Success': success,
        'Detected Green Color': green_color.tolist()  # Record detected green screen color
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

    # Build JSONL record
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
        description='Evaluate green background replacement quality without pretrained model.')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to input image')
    parser.add_argument('--output', type=str, required=True, help='Path to output image (green background)')
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