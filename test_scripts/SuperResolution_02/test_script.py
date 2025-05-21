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
    Calculate edge intensity (Sobel gradient) of an image.

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


def evaluate_super_resolution(input_path, output_path):
    """
    Evaluate super-resolution quality without pretrained model.

    Args:
        input_path (str): Path to input low-resolution image
        output_path (str): Path to output super-resolution image

    Returns:
        dict: Evaluation results containing PSNR, ESI, SSIM and success status
    """
    # Load images
    input_img = Image.open(input_path).convert('RGB')
    output_img = Image.open(output_path).convert('RGB')

    # Convert to numpy arrays
    input_array = np.array(input_img)
    output_array = np.array(output_img)

    # Check resolution (expect output to be 2x input)
    input_h, input_w = input_array.shape[:2]
    output_h, output_w = output_array.shape[:2]
    if output_h != 2 * input_h or output_w != 2 * input_w:
        return {
            'PSNR': 0.0,
            'PSNR Threshold': 20.0,
            'ESI (Edge Strength Improvement)': 0.0,
            'ESI Threshold': 1.2,
            'SSIM': 0.0,
            'SSIM Threshold': 0.8,
            'Success': False,
            'Error': f"Output resolution ({output_w}x{output_h}) is not 2x input ({input_w}x{input_h})"
        }

    # Upsample input image to output resolution (bilinear interpolation) as pseudo-reference
    upsampled_img = input_img.resize((output_w, output_h), Image.BILINEAR)
    upsampled_array = np.array(upsampled_img)

    # Calculate PSNR
    psnr_value = psnr(upsampled_array, output_array, data_range=255)

    # Calculate edge intensity
    input_edge = compute_edge_intensity(upsampled_array)
    output_edge = compute_edge_intensity(output_array)

    # Save edge intensity maps for debugging
    input_edge_img = Image.fromarray((input_edge / input_edge.max() * 255).astype(np.uint8))
    output_edge_img = Image.fromarray((output_edge / output_edge.max() * 255).astype(np.uint8))
    input_edge_img.save('input_edge.png')
    output_edge_img.save('output_edge.png')

    # Calculate ESI (Edge Strength Improvement)
    input_edge_mean = np.mean(input_edge)
    output_edge_mean = np.mean(output_edge)
    esi = output_edge_mean / (input_edge_mean + 1e-10)  # Avoid division by zero

    # —— Modified SSIM calculation section start ——
    h, w = output_array.shape[:2]
    min_side = min(h, w)
    win = min(7, min_side)
    if win % 2 == 0:
        win -= 1
    win = max(win, 3)
    try:
        ssim_value = ssim(
            upsampled_array,
            output_array,
            data_range=255,
            win_size=win,
            channel_axis=-1
        )
    except ValueError:
        ssim_value = ssim(
            upsampled_array,
            output_array,
            data_range=255,
            channel_axis=-1
        )
    # —— Modified SSIM calculation section end ——

    # Determine task success
    psnr_threshold = 18.0  # PSNR threshold
    esi_threshold = 1.2  # ESI threshold (20% edge strength improvement)
    ssim_threshold = 0.8  # SSIM threshold
    success = psnr_value >= psnr_threshold and esi >= esi_threshold and ssim_value >= ssim_threshold

    # Return results
    return {
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
    Validate input files exist, are non-empty, and have correct format.

    Returns:
        tuple: (bool, str) - (is valid, error message or empty string)
    """
    try:
        # Check file existence
        if not os.path.exists(input_path):
            return False, f"Input file {input_path} does not exist."
        if not os.path.exists(output_path):
            return False, f"Output file {output_path} does not exist."

        # Check files are non-empty
        if os.path.getsize(input_path) == 0:
            return False, f"Input file {input_path} is empty."
        if os.path.getsize(output_path) == 0:
            return False, f"Output file {output_path} is empty."

        # Check file format (try to open images)
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
        process (bool/numpy.bool_): Whether input parameters are valid
        result (bool/numpy.bool_): Whether evaluation succeeded
        comments (str): Additional information
    """
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    record = {
        "Process": bool(process),  # Convert to Python bool
        "Result": bool(result),  # Convert to Python bool
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
    parser = argparse.ArgumentParser(description='Evaluate super-resolution quality without pretrained model.')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to input low-resolution image')
    parser.add_argument('--output', type=str, required=True, help='Path to output super-resolution image')
    parser.add_argument('--result', type=str, help='Path to JSONL file to save results')

    args = parser.parse_args()

    # Validate input parameters
    process, comments = validate_inputs(args.groundtruth, args.output)

    # Initialize results
    result_dict = {}
    success = False

    # Run evaluation if inputs are valid
    if process:
        try:
            result_dict = evaluate_super_resolution(args.groundtruth, args.output)
            success = result_dict.get('Success', False)
            if 'Error' in result_dict:
                comments = result_dict['Error']
                success = False
            else:
                comments = (
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

    # Print results
    print('Evaluation Results:')
    if process and 'Error' not in result_dict:
        for key, value in result_dict.items():
            if key != 'Error':
                print(f'{key}: {value}')
    else:
        print(f'Error: {comments}')

    # Save results to JSONL (if --result provided)
    if args.result:
        save_result_to_jsonl(args.result, process, success, comments)


if __name__ == '__main__':
    main()