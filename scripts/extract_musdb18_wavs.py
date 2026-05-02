#!/usr/bin/env python3
"""Extract MUSDB18 .stem.mp4 files into a WAV folder tree.

The output layout matches the MATLAB PEASS script in scripts/peass.m:

    .temp_wavs/test/
      Track Name.stem/
        vocals.wav
        drums.wav
        bass.wav
        other.wav

By default the script also writes mixture.wav for convenience.

Usage:
    python scripts/extract_musdb18_wavs.py
    python scripts/extract_musdb18_wavs.py --input-dir data/musdb18/test --output-dir .temp_wavs/test
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_STEMS: Sequence[tuple[str, int]] = (
    ("mixture", 0),
    ("drums", 1),
    ("bass", 2),
    ("other", 3),
    ("vocals", 4),
)


def extract_track(source_path: Path, destination_dir: Path, stems: Sequence[tuple[str, int]]) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)

    for stem_name, stream_index in stems:
        output_path = destination_dir / f"{stem_name}.wav"
        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(source_path),
            "-map",
            f"0:a:{stream_index}",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
        subprocess.run(command, check=True)


def iter_source_files(input_dir: Path) -> Iterable[Path]:
    yield from sorted(input_dir.glob("*.stem.mp4"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract MUSDB18 .stem.mp4 files into WAV folders.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/musdb18/test"),
        help="Directory containing MUSDB18 .stem.mp4 files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".temp_wavs/test"),
        help="Destination root for extracted WAV folders.",
    )
    parser.add_argument(
        "--skip-mixture",
        action="store_true",
        help="Do not write mixture.wav, only the four stem files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    stems = DEFAULT_STEMS[1:] if args.skip_mixture else DEFAULT_STEMS
    source_files = list(iter_source_files(args.input_dir))
    if not source_files:
        raise FileNotFoundError(f"No .stem.mp4 files found in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for source_path in source_files:
        track_name = source_path.name.removesuffix(".mp4")
        destination_dir = args.output_dir / track_name
        print(f"Extracting {source_path.name} -> {destination_dir}")
        extract_track(source_path, destination_dir, stems)

    print(f"Done. Extracted {len(source_files)} track(s) into {args.output_dir}")


if __name__ == "__main__":
    main()