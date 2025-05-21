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
    """Check file exists, not empty, has valid extension, and can be read by soundfile."""
    if not os.path.isfile(path):
        return False, f'File does not exist: {path}'
    if os.path.getsize(path) == 0:
        return False, f'File is empty: {path}'
    if not path.lower().endswith('.wav'):
        return False, f'Unsupported format (requires .wav): {path}'
    try:
        data, sr = sf.read(path, dtype='float32')
        if data.size == 0:
            return False, f'Read empty data: {path}'
    except Exception as e:
        return False, f'Unable to read audio: {path} ({e})'
    return True, ''

def calc_snr(clean, est):
    """Calculate SNR = 10 log10( sum(clean^2) / sum((clean-est)^2) )"""
    noise = clean - est
    power_signal = np.sum(clean ** 2)
    power_noise = np.sum(noise ** 2) + 1e-8
    return 10 * np.log10(power_signal / power_noise)

def main():
    p = argparse.ArgumentParser(description='Automated speech separation evaluation script')
    p.add_argument('--groundtruth', required=True, help='Groundtruth directory containing input_original.wav, infer_boy.wav, infer_girl.wav')
    p.add_argument('--output', required=True,
                   help='Output directory containing output_01.wav, output_02.wav')
    p.add_argument('--snr_threshold', type=float, default=12.0, help='SNR threshold (dB)')
    p.add_argument('--sdr_threshold', type=float, default=8.0,  help='SDR threshold (dB)')
    p.add_argument('--result',        required=True, help='Result JSONL path (append mode)')
    args = p.parse_args()

    # Locate required files in groundtruth directory
    mixed_wav = os.path.join(args.groundtruth, 'input_original.wav')
    clean_wav_1 = os.path.join(args.groundtruth, 'infer_boy.wav')
    clean_wav_2 = os.path.join(args.groundtruth, 'infer_girl.wav')

    process = True
    comments = []

    # 1. Verify all input files
    for tag, path in [
        ('mixed', mixed_wav),
        ('clean1', clean_wav_1),
        ('clean2', clean_wav_2)
    ]:
        ok, msg = verify_wav(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')

    # 2. Verify output directory and files
    if not os.path.isdir(args.output):
        process = False
        comments.append(f'estimated_dir is not a directory: {args.output}')
    else:
        est1 = os.path.join(args.output, 'output_01.wav')
        est2 = os.path.join(args.output, 'output_02.wav')
        for tag, path in [('est1', est1), ('est2', est2)]:
            ok, msg = verify_wav(path)
            if not ok:
                process = False
                comments.append(f'[{tag}] {msg}')

    snr_vals = []
    sdr_vals = []

    # 3. Calculate metrics (only if process==True)
    if process:
        try:
            # Read audio files
            mix, sr0 = sf.read(mixed_wav, dtype='float32')
            c1,  sr1 = sf.read(clean_wav_1, dtype='float32')
            c2,  sr2 = sf.read(clean_wav_2, dtype='float32')
            e1,  sr3 = sf.read(est1, dtype='float32')
            e2,  sr4 = sf.read(est2, dtype='float32')

            # Sample rate consistency check (doesn't affect process)
            rates = {
                'mixed': sr0, 'clean1': sr1, 'clean2': sr2,
                'est1': sr3, 'est2': sr4
            }
            unique_rates = set(rates.values())
            if len(unique_rates) != 1:
                comments.append("Sample rates differ: " + ", ".join(f"{k}={v}" for k, v in rates.items()))

            # Mono conversion function
            def mono(x):
                return np.mean(x, axis=1) if x.ndim > 1 else x

            mix_m = mono(mix)
            c1_m  = mono(c1)
            c2_m  = mono(c2)
            e1_m  = mono(e1)
            e2_m  = mono(e2)

            # Truncate to minimum length
            minlen = min(len(c1_m), len(c2_m), len(e1_m), len(e2_m))
            c1_m = c1_m[:minlen]
            c2_m = c2_m[:minlen]
            e1_m = e1_m[:minlen]
            e2_m = e2_m[:minlen]

            # Construct reference and estimated matrices
            ref  = np.vstack([c1_m, c2_m])
            ests = np.vstack([e1_m, e2_m])

            # Calculate SDR (automatic matching)
            sdr, sir, sar, perm = bss_eval_sources(ref, ests)
            sdr_vals = [float(v) for v in sdr]

            # Calculate SNR based on permutation
            snr_list = []
            for i in range(2):
                ref_sig = ref[i]
                est_sig = ests[perm[i]]
                snr_list.append(float(calc_snr(ref_sig, est_sig)))
            snr_vals = snr_list

            # Record comments
            for i, v in enumerate(snr_vals, start=1):
                comments.append(f'SNR{i}={v:.2f} dB (threshold {args.snr_threshold})')
            for i, v in enumerate(sdr_vals, start=1):
                comments.append(f'SDR{i}={v:.2f} dB (threshold {args.sdr_threshold})')

        except Exception as e:
            process = False
            comments.append(f'Metric calculation error: {e}')

    # 4. Determine pass/fail
    result_flag = (
        process
        and all(v >= args.snr_threshold for v in snr_vals)
        and all(v >= args.sdr_threshold for v in sdr_vals)
    )

    # 5. Write JSONL
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

    # 6. Output final status (replaces original exit logic)
    print("Test complete - Status: " + ("PASS" if result_flag else "FAIL"))

if __name__ == "__main__":
    main()