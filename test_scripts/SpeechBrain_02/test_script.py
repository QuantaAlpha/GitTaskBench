import librosa
import numpy as np
from mir_eval.separation import bss_eval_sources, bss_eval_sources_framewise
import pydub
import argparse
import os
import json
from datetime import datetime

def evaluate_audio_separation(groundtruth_dir, output_dir):
    """
    Evaluate audio separation performance using SDR metric, considering SDR in [-100, 200] dB range as successful.

    Args:
        groundtruth_dir (str): Path to ground truth directory
        output_dir (str): Path to output directory

    Returns:
        dict: Dictionary containing SDR values and evaluation results
    """
    # Construct audio file paths
    mix_audio_path = os.path.join(groundtruth_dir, 'gt.mp3')
    sep_audio1_path = os.path.join(groundtruth_dir, 'gt_01.wav')
    sep_audio2_path = os.path.join(groundtruth_dir, 'gt_02.wav')
    ref_audio1_path = os.path.join(output_dir, 'output_01.wav')
    ref_audio2_path = os.path.join(output_dir, 'output_02.wav')

    # Load audio
    def load_audio(file_path, sr=22050):
        if file_path.endswith('.mp3'):
            try:
                audio = pydub.AudioSegment.from_mp3(file_path)
                audio = audio.set_channels(1)  # Convert to mono
                samples = np.array(audio.get_array_of_samples())
                audio_data = samples.astype(np.float32) / np.iinfo(samples.dtype).max
                return audio_data, sr
            except Exception as e:
                raise ValueError(f"Failed to load MP3 {file_path}: {str(e)}")
        else:
            try:
                return librosa.load(file_path, sr=sr, mono=True)
            except Exception as e:
                raise ValueError(f"Failed to load WAV {file_path}: {str(e)}")

    # Pre-check audio validity
    def validate_audio(audio, path):
        if len(audio) == 0:
            raise ValueError(f"Audio is empty: {path}")
        if np.all(audio == 0):
            raise ValueError(f"Audio is silent (all zeros): {path}")
        if np.any(np.isnan(audio)) or np.any(np.isinf(audio)):
            raise ValueError(f"Audio contains NaN or Inf: {path}")

    # Load mixed and separated audio
    try:
        mix_audio, sr = load_audio(mix_audio_path)
        sep_audio1, _ = load_audio(sep_audio1_path, sr)
        sep_audio2, _ = load_audio(sep_audio2_path, sr)
    except Exception as e:
        return {
            'mean_sdr': None,
            'is_acceptable': False,
            'message': f"Audio loading failed: {str(e)}"
        }

    # Validate audio content
    try:
        validate_audio(mix_audio, mix_audio_path)
        validate_audio(sep_audio1, sep_audio1_path)
        validate_audio(sep_audio2, sep_audio2_path)
    except Exception as e:
        return {
            'mean_sdr': None,
            'is_acceptable': False,
            'message': f"Audio validation failed: {str(e)}"
        }

    # Ensure consistent audio length
    min_length = min(len(mix_audio), len(sep_audio1), len(sep_audio2))
    if min_length < sr / 10:  # Ensure audio is at least 0.1 seconds
        return {
            'mean_sdr': None,
            'is_acceptable': False,
            'message': f"Audio too short: {min_length/sr:.2f} seconds"
        }
    mix_audio = mix_audio[:min_length]
    sep_audio1 = sep_audio1[:min_length]
    sep_audio2 = sep_audio2[:min_length]

    try:
        ref_audio1, _ = load_audio(ref_audio1_path, sr)
        ref_audio2, _ = load_audio(ref_audio2_path, sr)
        validate_audio(ref_audio1, ref_audio1_path)
        validate_audio(ref_audio2, ref_audio2_path)
        ref_audio1 = ref_audio1[:min_length]
        ref_audio2 = ref_audio2[:min_length]
    except Exception as e:
        return {
            'mean_sdr': None,
            'is_acceptable': False,
            'message': f"Reference audio loading/validation failed: {str(e)}"
        }

    # Calculate SDR (prefer newer function, fallback to older one)
    try:
        try:
            # Try using newer framewise function
            sdr, _, _, _ = bss_eval_sources_framewise(
                reference_sources=np.array([ref_audio1, ref_audio2]),
                estimated_sources=np.array([sep_audio1, sep_audio2]),
                compute_permutation=True
            )
        except AttributeError:
            # Fallback to older function
            sdr, _, _, _ = bss_eval_sources(
                reference_sources=np.array([ref_audio1, ref_audio2]),
                estimated_sources=np.array([sep_audio1, sep_audio2]),
                compute_permutation=True
            )
    except Exception as e:
        return {
            'mean_sdr': None,
            'is_acceptable': False,
            'message': f"SDR calculation failed: {str(e)}"
        }

    # Average SDR
    mean_sdr = np.mean(sdr)

    # Check if SDR is within [-100, 200] dB range
    is_acceptable = -100 <= mean_sdr <= 200
    message = f"Mean SDR: {mean_sdr:.2f} dB, {'Acceptable' if is_acceptable else 'Unacceptable'} (Range: [-100, 200] dB)"

    # Evaluation results
    result = {
        'mean_sdr': float(mean_sdr) if mean_sdr is not None else None,
        'is_acceptable': is_acceptable,
        'message': message
    }

    return result

def check_file_validity(file_path):
    """Check if file exists, is not empty, and has correct format"""
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    if not (file_path.endswith('.mp3') or file_path.endswith('.wav')):
        return False, f"Invalid file format: {file_path}"
    return True, ""

def main():
    parser = argparse.ArgumentParser(description="Evaluate audio separation using SDR metric.")
    parser.add_argument('--groundtruth', type=str, required=True, help="Path to the ground truth directory")
    parser.add_argument('--output', type=str, required=True, help="Path to the output directory")
    parser.add_argument('--result', type=str, default=None, help="Path to JSONL file to store results")

    args = parser.parse_args()

    # Construct audio file paths
    mix_audio_path = os.path.join(args.groundtruth, 'gt.mp3')
    sep_audio1_path = os.path.join(args.groundtruth, 'gt_01.wav')
    sep_audio2_path = os.path.join(args.groundtruth, 'gt_02.wav')
    ref_audio1_path = os.path.join(args.output, 'output_01.wav')
    ref_audio2_path = os.path.join(args.output, 'output_02.wav')

    # Check file validity
    comments = []
    process_success = True
    for path in [mix_audio_path, sep_audio1_path, sep_audio2_path, ref_audio1_path, ref_audio2_path]:
        is_valid, comment = check_file_validity(path)
        if not is_valid:
            process_success = False
            comments.append(comment)

    # Initialize result dictionary
    result_dict = {
        "Process": process_success,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }

    # If Process failed, save results directly
    if not process_success:
        result_dict["comments"] = "; ".join(comments)
    else:
        try:
            # Run evaluation
            result = evaluate_audio_separation(
                groundtruth_dir=args.groundtruth,
                output_dir=args.output
            )

            # Update results
            result_dict["Result"] = result['is_acceptable']
            result_dict["comments"] = result['message']
            print(result['message'])
        except Exception as e:
            result_dict["Result"] = False
            result_dict["comments"] = f"Evaluation failed: {str(e)}"
            comments.append(str(e))

    # If result file path specified, save to JSONL
    if args.result:
        try:
            # Ensure proper boolean serialization
            serializable_dict = {
                "Process": bool(result_dict["Process"]),  # Explicitly convert to boolean
                "Result": bool(result_dict["Result"]),
                "TimePoint": result_dict["TimePoint"],
                "comments": result_dict["comments"]
            }
            with open(args.result, 'a', encoding='utf-8') as f:
                json_line = json.dumps(serializable_dict, ensure_ascii=False)
                f.write(json_line + '\n')
        except Exception as e:
            print(f"Failed to save results to {args.result}: {str(e)}")
            # As fallback, use default=str
            try:
                with open(args.result, 'a', encoding='utf-8') as f:
                    json_line = json.dumps(result_dict, ensure_ascii=False, default=str)
                    f.write(json_line + '\n')
                print(f"Retried with default=str, successfully saved to {args.result}")
            except Exception as e2:
                print(f"Retry failed: {str(e2)}")

if __name__ == "__main__":
    main()