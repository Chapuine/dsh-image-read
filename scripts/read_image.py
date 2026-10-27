#!/usr/bin/env python3
"""dsh-image-read 图片预处理脚本。

将用户提供的图片规范化为模型可读的形式：
- 校验文件存在与格式支持
- 按 EXIF 自动摆正方向
- 默认转换为 JPEG（--keep-format 保留 PNG/透明通道）
- 高度超过 --split-height 时先按重叠切片拆分（长截图/长图保留细节）
- 再对每块（或整图）等比降采样，边长不超过 --max-size
- 输出 JSON 摘要

用法示例：
    python3 read_image.py /path/to/image.png --output-dir /tmp/img_out
    python3 read_image.py /path/to/long_screenshot.jpg --split-height 4096 --overlap 200
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageOps

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif"}


def parse_args():
    p = argparse.ArgumentParser(description="dsh-image-read 图片预处理")
    p.add_argument("input", help="输入图片路径")
    p.add_argument("--output-dir", default=None,
                   help="输出目录（默认：输入图片同目录下的 processed/）")
    p.add_argument("--max-size", type=int, default=2048,
                   help="最大边长（像素），超过则等比降采样，默认 2048")
    p.add_argument("--split-height", type=int, default=4096,
                   help="高度超过该值（像素）则切片，默认 4096")
    p.add_argument("--overlap", type=int, default=200,
                   help="相邻切片重叠像素数，默认 200")
    p.add_argument("--keep-format", action="store_true",
                   help="保留 PNG（含透明通道），默认转换为 JPEG")
    p.add_argument("--no-split", action="store_true", help="禁止切片")
    return p.parse_args()


def fail(message):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    sys.exit(1)


def main():
    args = parse_args()

    if args.max_size <= 0:
        fail("--max-size 必须为正数")
    if args.split_height <= 0:
        fail("--split-height 必须为正数")
    if args.overlap < 0:
        fail("--overlap 不能为负数")
    if args.overlap >= args.split_height:
        fail("--overlap 必须小于 --split-height")

    src = os.path.abspath(args.input)
    if not os.path.isfile(src):
        fail(f"文件不存在: {src}")

    ext = os.path.splitext(src)[1].lower()
    if ext not in SUPPORTED_EXT:
        fail(f"不支持的格式: {ext}（支持: {sorted(SUPPORTED_EXT)}）")

    try:
        img = Image.open(src)
        img = ImageOps.exif_transpose(img)  # 按 EXIF 摆正
        img.load()
    except Exception as e:
        fail(f"图片读取失败: {e}")

    # 统一色彩模式：先归一化模式，再统一处理透明通道
    if img.mode == "P":
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")
    elif img.mode == "LA":
        img = img.convert("RGBA")
    elif img.mode in ("CMYK", "I", "I;16", "F"):
        img = img.convert("RGB")

    if img.mode == "RGBA":
        if args.keep_format:
            pass  # 保留 RGBA，输出 PNG
        else:
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg

    out_dir = args.output_dir or os.path.join(os.path.dirname(src), "processed")
    os.makedirs(out_dir, exist_ok=True)

    orig_w, orig_h = img.size
    w, h = img.size

    fmt = "PNG" if args.keep_format and img.mode == "RGBA" else "JPEG"
    ext_out = ".png" if fmt == "PNG" else ".jpg"
    base = os.path.splitext(os.path.basename(src))[0]

    # 第 1 步：切片（在降采样之前，保证长图每一块保留原始细节）
    pieces = [(img, 0, h)]  # (image, top, bottom)
    if not args.no_split and h > args.split_height:
        step = args.split_height - args.overlap
        top = 0
        pieces = []
        while top < h:
            # 剩余高度不足 overlap 时已在前一块的重叠区域内，不再单独成块
            if h - top <= args.overlap:
                break
            bottom = min(h, top + args.split_height)
            pieces.append((img.crop((0, top, w, bottom)), top, bottom))
            top += step

    # 第 2 步：逐块等比降采样，保证每块边长不超过模型上限
    files = []
    for idx, (piece, top, bottom) in enumerate(pieces, start=1):
        pw, ph = piece.size
        scale = 1.0
        if max(pw, ph) > args.max_size:
            scale = args.max_size / float(max(pw, ph))
            piece = piece.resize(
                (max(1, round(pw * scale)), max(1, round(ph * scale))), Image.LANCZOS)
        if len(pieces) == 1:
            name = f"{base}_processed{ext_out}"
        else:
            name = f"{base}_chunk{idx:02d}{ext_out}"
        path = os.path.join(out_dir, name)
        piece.save(path, fmt, **({"quality": 95} if fmt == "JPEG" else {}))
        files.append({
            "file": path,
            "size": list(piece.size),
            "y_range": [top, bottom],
            "scale": round(scale, 4),
        })

    result = {
        "ok": True,
        "input": src,
        "original_size": [orig_w, orig_h],
        "format": fmt,
        "split": len(pieces) > 1,
        "output_dir": out_dir,
        "files": files,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
