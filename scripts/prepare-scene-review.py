#!/usr/bin/env python3
"""Create cross-platform FFmpeg review frames and media metadata."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def resolve_tool(explicit: Optional[str], name: str) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        raise SystemExit(f"{name} not found at explicit path: {candidate}")

    found = shutil.which(name)
    if found:
        return found

    suffix = ".exe" if os.name == "nt" else ""
    for directory in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        candidate = directory / f"{name}{suffix}"
        if candidate.is_file():
            return str(candidate)

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            winget_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_root.is_dir():
                matches = winget_root.glob(f"**/{name}.exe")
                first = next(matches, None)
                if first:
                    return str(first)

    raise SystemExit(
        f"{name} was not found. Install FFmpeg or pass --{name} with an explicit path."
    )


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture else None,
        )
    except subprocess.CalledProcessError as exc:
        rendered = " ".join(command[:2])
        raise SystemExit(f"Command failed ({exc.returncode}): {rendered}") from exc


def remove_generated(directory: Path, pattern: str) -> None:
    for path in directory.glob(pattern):
        if path.is_file():
            path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract fixed-interval and scene-change frames for semantic video review."
    )
    parser.add_argument("--video", required=True, type=Path, help="Source video path")
    parser.add_argument("--output", required=True, type=Path, help="Review output directory")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between fixed frames")
    parser.add_argument(
        "--scene-threshold", type=float, default=0.08, help="FFmpeg scene-change threshold"
    )
    parser.add_argument("--scale-width", type=int, default=540, help="Review frame width")
    parser.add_argument("--ffmpeg", help="Explicit ffmpeg executable path")
    parser.add_argument("--ffprobe", help="Explicit ffprobe executable path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.interval <= 0:
        raise SystemExit("--interval must be positive")
    if not 0 <= args.scene_threshold < 1:
        raise SystemExit("--scene-threshold must be in [0, 1)")
    if args.scale_width < 2:
        raise SystemExit("--scale-width must be at least 2")

    video = args.video.expanduser().resolve()
    if not video.is_file():
        raise SystemExit(f"Video not found: {video}")

    output = args.output.expanduser().resolve()
    fixed_dir = output / "fixed"
    scene_dir = output / "scene-change"
    fixed_dir.mkdir(parents=True, exist_ok=True)
    scene_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = resolve_tool(args.ffmpeg, "ffmpeg")
    ffprobe = resolve_tool(args.ffprobe, "ffprobe")

    probe = run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        capture=True,
    )
    (output / "media-probe.json").write_text(probe.stdout, encoding="utf-8")

    remove_generated(fixed_dir, "fixed-*.jpg")
    remove_generated(scene_dir, "scene-*.png")

    fixed_filter = f"fps=1/{args.interval:g},scale={args.scale_width}:-2"
    run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            fixed_filter,
            "-q:v",
            "3",
            "-y",
            str(fixed_dir / "fixed-%05d.jpg"),
        ]
    )

    scene_filter = f"select=gt(scene\\,{args.scene_threshold:g}),scale={args.scale_width}:-2"
    run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            scene_filter,
            "-fps_mode",
            "vfr",
            "-y",
            str(scene_dir / "scene-%05d.png"),
        ]
    )

    fixed = sorted(fixed_dir.glob("fixed-*.jpg"))
    scene = sorted(scene_dir.glob("scene-*.png"))
    with (output / "fixed-frames.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["frame", "approx_seconds"])
        writer.writeheader()
        for index, frame in enumerate(fixed):
            writer.writerow(
                {"frame": frame.name, "approx_seconds": round(index * args.interval, 3)}
            )

    summary = {
        "video": str(video),
        "platform": platform.system(),
        "python": sys.version.split()[0],
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "fixed_frames": len(fixed),
        "scene_change_frames": len(scene),
        "interval_seconds": args.interval,
        "scene_threshold": args.scene_threshold,
        "scale_width": args.scale_width,
    }
    summary_path = output / "review-summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
