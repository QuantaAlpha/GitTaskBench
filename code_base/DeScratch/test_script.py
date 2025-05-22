#!/usr/bin/env python3
import argparse
import os
import json
import datetime
import numpy as np
from PIL import Image, UnidentifiedImageError

def main():
    parser = argparse.ArgumentParser(description='自动化划痕检测测试脚本')
    parser.add_argument(
        '--output',
        required=True,
        help='待检测的输出JPEG图像路径'
    )
    parser.add_argument(
        '--result',
        required=True,
        help='结果JSONL文件路径（不存在则新建，存在则追加）'
    )
    args = parser.parse_args()

    process = False
    result = False
    comments = []

    # —— 一、检验输入文件合法性 —— 
    if not os.path.isfile(args.output):
        comments.append(f'文件不存在：{args.output}')
    elif os.path.getsize(args.output) == 0:
        comments.append(f'文件为空：{args.output}')
    else:
        try:
            # verify 格式
            img = Image.open(args.output)
            img.verify()
            process = True

            # 重新打开，读取像素
            img = Image.open(args.output)
            arr = np.array(img)

            # 将多通道图像转为单通道
            if arr.ndim == 3:
                channel = arr[..., 0]
            else:
                channel = arr

            # —— 二、判断mask是否全黑 —— 
            # 只要有任意像素值 > 0，就视为“有划痕”
            white_px = np.count_nonzero(channel > 0)
            if white_px > 0:
                comments.append(f'检测到白色像素 {white_px} 个，疑似划痕')
                result = False
            else:
                comments.append('未检测到白色像素，mask 全黑，无划痕')
                result = True

        except UnidentifiedImageError as e:
            comments.append(f'无效的图像格式：{e}')
        except Exception as e:
            comments.append(f'读取图像出错：{e}')

    # —— 三、写入 JSONL —— 
    entry = {
        "Process": process,
        "Result" : result,
        "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
        "comments": "; ".join(comments)
    }

    # 追加模式写入，每条一行
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # 退出码：  # 改成总是 0
    exit(0)


if __name__ == "__main__":
    main()
