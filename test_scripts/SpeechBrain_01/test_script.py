#!/usr/bin/env python3
import os
import sys
import argparse
import json
import datetime
import numpy as np
import soundfile as sf
from mir_eval.separation import bss_eval_sources

def verify_wav(path):
    """检查文件存在、非空、扩展名合法，并能被 soundfile 读取。"""
    if not os.path.isfile(path):
        return False, f'文件不存在：{path}'
    if os.path.getsize(path) == 0:
        return False, f'文件为空：{path}'
    if not path.lower().endswith('.wav'):
        return False, f'不支持的格式（需 .wav）：{path}'
    try:
        data, sr = sf.read(path, dtype='float32')
        if data.size == 0:
            return False, f'读取到空数据：{path}'
    except Exception as e:
        return False, f'无法读取音频：{path} （{e}）'
    return True, ''

def calc_snr(clean, est):
    """计算 SNR = 10 log10( sum(clean^2) / sum((clean–est)^2) )"""
    noise = clean - est
    power_signal = np.sum(clean ** 2)
    power_noise = np.sum(noise ** 2) + 1e-8
    return 10 * np.log10(power_signal / power_noise)

def main():
    p = argparse.ArgumentParser(description='自动化语音分离效果检测脚本')
    p.add_argument('--mixed_wav',     required=True, help='原始混合语音 WAV')
    p.add_argument('--clean_wav_1',   required=True, help='纯净男声 WAV')
    p.add_argument('--clean_wav_2',   required=True, help='纯净女声 WAV')
    p.add_argument('--output', required=True,
                   help='分离后输出目录，包含 output_01.wav, output_02.wav')
    p.add_argument('--snr_threshold', type=float, default=12.0, help='SNR 阈值 (dB)')
    p.add_argument('--sdr_threshold', type=float, default=8.0,  help='SDR 阈值 (dB)')
    p.add_argument('--result',        required=True, help='结果 JSONL 路径（追加模式）')
    args = p.parse_args()

    process = True
    comments = []

    # 1. 验证所有输入文件
    for tag, path in [
        ('mixed', args.mixed_wav),
        ('clean1', args.clean_wav_1),
        ('clean2', args.clean_wav_2)
    ]:
        ok, msg = verify_wav(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')


    # 2. 验证输出目录及文件
    if not os.path.isdir(args.estimated_dir):
        process = False
        comments.append(f'estimated_dir 不是目录：{args.estimated_dir}')
    else:
        est1 = os.path.join(args.estimated_dir, 'output_01.wav')
        est2 = os.path.join(args.estimated_dir, 'output_02.wav')
        for tag, path in [('est1', est1), ('est2', est2)]:
            ok, msg = verify_wav(path)
            if not ok:
                process = False
                comments.append(f'[{tag}] {msg}')

    snr_vals = []
    sdr_vals = []

    # 3. 计算指标（仅当 process==True）
    if process:
        try:
            # 读取音频
            mix, sr0 = sf.read(args.mixed_wav, dtype='float32')
            c1,  sr1 = sf.read(args.clean_wav_1, dtype='float32')
            c2,  sr2 = sf.read(args.clean_wav_2, dtype='float32')
            e1,  sr3 = sf.read(est1, dtype='float32')
            e2,  sr4 = sf.read(est2, dtype='float32')

            # 采样率一致性检查（不影响 process）
            rates = {
                'mixed': sr0, 'clean1': sr1, 'clean2': sr2,
                'est1': sr3, 'est2': sr4
            }
            unique_rates = set(rates.values())
            if len(unique_rates) != 1:
                comments.append("采样率不一致: " + ", ".join(f"{k}={v}" for k, v in rates.items()))

            # 单通道化函数
            def mono(x):
                return np.mean(x, axis=1) if x.ndim > 1 else x

            mix_m = mono(mix)
            c1_m  = mono(c1)
            c2_m  = mono(c2)
            e1_m  = mono(e1)
            e2_m  = mono(e2)

            # 截断到最小长度
            minlen = min(len(c1_m), len(c2_m), len(e1_m), len(e2_m))
            c1_m = c1_m[:minlen]
            c2_m = c2_m[:minlen]
            e1_m = e1_m[:minlen]
            e2_m = e2_m[:minlen]

            # 构造 reference 和 estimated 矩阵
            ref  = np.vstack([c1_m, c2_m])
            ests = np.vstack([e1_m, e2_m])

            # 计算 SDR（自动匹配）
            sdr, sir, sar, perm = bss_eval_sources(ref, ests)
            sdr_vals = [float(v) for v in sdr]

            # 依据 perm 计算 SNR
            snr_list = []
            for i in range(2):
                ref_sig = ref[i]
                est_sig = ests[perm[i]]
                snr_list.append(float(calc_snr(ref_sig, est_sig)))
            snr_vals = snr_list

            # 记录 comments
            for i, v in enumerate(snr_vals, start=1):
                comments.append(f'SNR{i}={v:.2f} dB (阈值 {args.snr_threshold})')
            for i, v in enumerate(sdr_vals, start=1):
                comments.append(f'SDR{i}={v:.2f} dB (阈值 {args.sdr_threshold})')

        except Exception as e:
            process = False
            comments.append(f'指标计算出错：{e}')

    # 4. 判定通过与否
    result_flag = (
        process
        and all(v >= args.snr_threshold for v in snr_vals)
        and all(v >= args.sdr_threshold for v in sdr_vals)
    )

    # 5. 写入 JSONL
    entry = {
        "Process":  process,
        "Result":   result_flag,
        "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
        "comments":  "; ".join(comments)
    }
    print("; ".join(comments))
    os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # 6. 输出最终状态（替代原退出逻辑）
    print("测试完成 - 状态: " + ("通过" if result_flag else "未通过"))

if __name__ == "__main__":
    main()