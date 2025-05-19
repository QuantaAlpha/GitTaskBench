import librosa
import numpy as np
from mir_eval.separation import bss_eval_sources, bss_eval_sources_framewise
import pydub
import argparse
import os
import json
from datetime import datetime

def evaluate_audio_separation(mix_audio_path, sep_audio1_path, sep_audio2_path, ref_audio1_path=None, ref_audio2_path=None):
    """
    评估音频分离效果，使用SDR指标，SDR在[-100, 200] dB范围内视为成功。
    
    Args:
        mix_audio_path (str): 原始混音MP3文件路径
        sep_audio1_path (str): 分离出的第一个WAV音频路径
        sep_audio2_path (str): 分离出的第二个WAV音频路径
        ref_audio1_path (str, optional): 第一个参考WAV音频路径
        ref_audio2_path (str, optional): 第二个参考WAV音频路径
    
    Returns:
        dict: 包含SDR值和评估结果的字典
    """
    # 加载音频
    def load_audio(file_path, sr=22050):
        if file_path.endswith('.mp3'):
            try:
                audio = pydub.AudioSegment.from_mp3(file_path)
                audio = audio.set_channels(1)  # 转换为单声道
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

    # 预检查音频有效性
    def validate_audio(audio, path):
        if len(audio) == 0:
            raise ValueError(f"Audio is empty: {path}")
        if np.all(audio == 0):
            raise ValueError(f"Audio is silent (all zeros): {path}")
        if np.any(np.isnan(audio)) or np.any(np.isinf(audio)):
            raise ValueError(f"Audio contains NaN or Inf: {path}")

    # 加载混音和分离音频
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

    # 验证音频内容
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

    # 确保音频长度一致
    min_length = min(len(mix_audio), len(sep_audio1), len(sep_audio2))
    if min_length < sr / 10:  # 确保音频至少0.1秒
        return {
            'mean_sdr': None,
            'is_acceptable': False,
            'message': f"Audio too short: {min_length/sr:.2f} seconds"
        }
    mix_audio = mix_audio[:min_length]
    sep_audio1 = sep_audio1[:min_length]
    sep_audio2 = sep_audio2[:min_length]

    # 如果没有提供参考音频，假设分离音频之和近似混音
    if ref_audio1_path is None or ref_audio2_path is None:
        ref_audio1 = sep_audio1
        ref_audio2 = sep_audio2
    else:
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

    # 计算SDR（优先使用新函数，兼容旧函数）
    try:
        try:
            # 尝试使用新版 framewise 函数
            sdr, _, _, _ = bss_eval_sources_framewise(
                reference_sources=np.array([ref_audio1, ref_audio2]),
                estimated_sources=np.array([sep_audio1, sep_audio2]),
                compute_permutation=True
            )
        except AttributeError:
            # 回退到旧版函数
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

    # 平均SDR
    mean_sdr = np.mean(sdr)
    
    # 检查SDR值是否在[-100, 200] dB范围内
    is_acceptable = -100 <= mean_sdr <= 200
    message = f"Mean SDR: {mean_sdr:.2f} dB, {'Acceptable' if is_acceptable else 'Unacceptable'} (Range: [-100, 200] dB)"
    
    # 评估结果
    result = {
        'mean_sdr': float(mean_sdr) if mean_sdr is not None else None,
        'is_acceptable': is_acceptable,
        'message': message
    }

    return result

def check_file_validity(file_path):
    """检查文件是否存在、非空、格式正确"""
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    if not (file_path.endswith('.mp3') or file_path.endswith('.wav')):
        return False, f"Invalid file format: {file_path}"
    return True, ""

def main():
    parser = argparse.ArgumentParser(description="Evaluate audio separation using SDR metric.")
    parser.add_argument('--mix', type=str, required=True, help="Path to the original mixed MP3 audio")
    parser.add_argument('--sep1', type=str, required=True, help="Path to the first separated WAV audio")
    parser.add_argument('--sep2', type=str, required=True, help="Path to the second separated WAV audio")
    parser.add_argument('--ref1', type=str, default=None, help="Path to the first reference WAV audio (optional)")
    parser.add_argument('--ref2', type=str, default=None, help="Path to the second reference WAV audio (optional)")
    parser.add_argument('--result', type=str, default=None, help="Path to JSONL file to store results")

    args = parser.parse_args()

    # 检查文件有效性
    comments = []
    process_success = True
    for path in [args.mix, args.sep1, args.sep2]:
        is_valid, comment = check_file_validity(path)
        if not is_valid:
            process_success = False
            comments.append(comment)
    
    # 如果有参考音频，检查其有效性
    for path in [args.ref1, args.ref2]:
        if path:
            is_valid, comment = check_file_validity(path)
            if not is_valid:
                process_success = False
                comments.append(comment)

    # 初始化结果字典
    result_dict = {
        "Process": process_success,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }

    # 如果 Process 失败，直接保存结果
    if not process_success:
        result_dict["comments"] = "; ".join(comments)
    else:
        try:
            # 运行评估
            result = evaluate_audio_separation(
                mix_audio_path=args.mix,
                sep_audio1_path=args.sep1,
                sep_audio2_path=args.sep2,
                ref_audio1_path=args.ref1,
                ref_audio2_path=args.ref2
            )

            # 更新结果
            result_dict["Result"] = result['is_acceptable']
            result_dict["comments"] = result['message']
            print(result['message'])
        except Exception as e:
            result_dict["Result"] = False
            result_dict["comments"] = f"Evaluation failed: {str(e)}"
            comments.append(str(e))

    # 如果指定了 result 文件路径，保存到 JSONL
    if args.result:
        try:
            # 确保布尔值序列化正确
            serializable_dict = {
                "Process": bool(result_dict["Process"]),  # 显式转换为布尔值
                "Result": bool(result_dict["Result"]),
                "TimePoint": result_dict["TimePoint"],
                "comments": result_dict["comments"]
            }
            with open(args.result, 'a', encoding='utf-8') as f:
                json_line = json.dumps(serializable_dict, ensure_ascii=False)
                f.write(json_line + '\n')
        except Exception as e:
            print(f"Failed to save results to {args.result}: {str(e)}")
            # 作为后备，使用 default=str
            try:
                with open(args.result, 'a', encoding='utf-8') as f:
                    json_line = json.dumps(result_dict, ensure_ascii=False, default=str)
                    f.write(json_line + '\n')
                print(f"Retried with default=str, successfully saved to {args.result}")
            except Exception as e2:
                print(f"Retry failed: {str(e2)}")

if __name__ == "__main__":
    main()