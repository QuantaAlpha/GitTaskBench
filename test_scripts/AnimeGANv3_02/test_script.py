#!/usr/bin/env python3
import os
import sys
import argparse
import json
import datetime
import cv2
import torch
import lpips
from torchvision import transforms
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError

def verify_image(path, exts=('.png','.jpg','.jpeg','.webp')):
    if not os.path.isfile(path):
        return False, f'File does not exist: {path}'
    if os.path.getsize(path) == 0:
        return False, f'File is empty: {path}'
    if not path.lower().endswith(exts):
        return False, f'Unsupported format: {path}'
    try:
        img = Image.open(path)
        img.verify()
    except (UnidentifiedImageError, Exception) as e:
        return False, f'Failed to read image: {path} ({e})'
    return True, ''

def load_tensor(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f'cv2 read failed: {path}')
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    t = transforms.ToTensor()(img) * 2 - 1
    return t.unsqueeze(0)

def main():
    p = argparse.ArgumentParser(description='Automated anime effect evaluation script')
    p.add_argument('--groundtruth', required=True, help='Original image path')
    p.add_argument('--output', required=True, help='Anime-styled output image path')
    p.add_argument('--lpips-thresh', type=float, default=0.40,
                   help='LPIPS structural similarity max distance (Pass if <= threshold)')
    p.add_argument('--clip-thresh', type=float, default=0.25,
                   help='CLIP anime style similarity threshold (Pass if > threshold)')
    p.add_argument('--result', required=True, help='Result JSONL file path (append mode)')
    args = p.parse_args()

    process = True
    comments = []

    # 1. Validate input/output files
    for tag, path in [('input', args.groundtruth), ('output', args.output)]:
        ok, msg = verify_image(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')

    lpips_val = None
    lpips_pass = True
    clip_pass = False
    if process:
        try:
            # 2. LPIPS structure preservation check
            img0 = load_tensor(args.groundtruth)
            img1 = load_tensor(args.output)
            _, _, h0, w0 = img0.shape
            _, _, h1, w1 = img1.shape
            nh, nw = min(h0,h1), min(w0,w1)
            img0 = F.interpolate(img0, size=(nh,nw), mode='bilinear', align_corners=False)
            img1 = F.interpolate(img1, size=(nh,nw), mode='bilinear', align_corners=False)

            loss_fn = lpips.LPIPS(net='vgg').to(torch.device('cpu'))
            with torch.no_grad():
                lpips_val = float(loss_fn(img0, img1).item())
            lpips_pass = lpips_val <= args.lpips_thresh
            comments.append(f'LPIPS={lpips_val:.4f} (<= {args.lpips_thresh} → {"OK" if lpips_pass else "FAIL"})')
        except Exception as e:
            process = False
            comments.append(f'Metric calculation error: {e}')

    if process:
        try:
            import clip
            import PIL.Image
            device = "cuda" if torch.cuda.is_available() else "cpu"
            clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)

            image = clip_preprocess(PIL.Image.open(args.output)).unsqueeze(0).to(device)
            prompt_list = [
                "anime-style photo",
                "cartoon photo",
                "anime drawing",
                "photo in manga style",
                "Hayao Miyazaki anime style"
            ]
            tokens = clip.tokenize(prompt_list).to(device)

            with torch.no_grad():
                image_features = clip_model.encode_image(image)
                text_features = clip_model.encode_text(tokens)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                scores = (image_features @ text_features.T).squeeze(0)
                best_score = scores.max().item()

            clip_pass = best_score > args.clip_thresh
            comments.append(f'CLIP best anime style score = {best_score:.3f} (>{args.clip_thresh} → {"OK" if clip_pass else "FAIL"})')

        except Exception as e:
            comments.append(f"CLIP style check failed: {e}")

    result_flag = process and lpips_pass and clip_pass

    # 4. Write JSONL result
    entry = {
        "Process": process,
        "Result": result_flag,
        "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
        "comments": "; ".join(comments)
    }
    os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

if __name__ == "__main__":
    main()
