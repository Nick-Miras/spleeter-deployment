"""
evaluate_spleeter.py
====================
Custom evaluation script for Spleeter that computes:
  - SDR  (Signal-to-Distortion Ratio)
  - SIR  (Signal-to-Interference Ratio)
  - SAR  (Signal-to-Artifacts Ratio)

Dependencies:
    pip install spleeter mir_eval librosa numpy pandas soundfile stempeg

Usage:
    # Evaluate directly from a .stem.mp4 file (NI Stem format)
    python evaluate_spleeter.py \
        --stem-mp4  path/to/track.stem.mp4 \
        --model     spleeter:4stems \
        --out       results.csv

    # Evaluate a single mixture WAV against ground-truth stems folder
    python evaluate_spleeter.py \
        --mixture  path/to/mixture.wav \
        --stems    path/to/stems_dir/ \
        --model    spleeter:2stems \
        --out      results.csv

    # Batch-evaluate a whole dataset (MUSDB-style folder layout)
    python evaluate_spleeter.py \
        --dataset  path/to/dataset/ \
        --model    spleeter:2stems \
        --out      results.csv

    # Batch-evaluate a folder of .stem.mp4 files
    python evaluate_spleeter.py \
        --dataset  path/to/dataset/ \
        --stem-mp4-batch \
        --model    spleeter:4stems \
        --out      results.csv

Dataset folder layout for --dataset (WAV mode):
    dataset/
      track_01/
        mixture.wav
        vocals.wav
        accompaniment.wav   # or bass.wav / drums.wav / other.wav for 4stems
      track_02/
        ...

Dataset folder layout for --dataset --stem-mp4-batch:
    dataset/
      track_01.stem.mp4
      track_02.stem.mp4
      ...

.stem.mp4 track layout (NI Stem format):
    Track 0  →  full mix  (used as the Spleeter input)
    Track 1+ →  individual stems  (used as ground-truth references)

Stem names are read from the file's JSON metadata when available.
Use --stem-names to override: --stem-names vocals drums bass other
"""

import argparse
import json
import os
import tempfile
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import librosa
import mir_eval
import numpy as np
import pandas as pd
import soundfile as sf

warnings.filterwarnings("ignore")

# ── Spleeter stem names per model ─────────────────────────────────────────────
STEM_MAP = {
    "spleeter:2stems": ["vocals", "accompaniment"],
    "spleeter:4stems": ["vocals", "drums", "bass", "other"],
    "spleeter:5stems": ["vocals", "drums", "bass", "piano", "other"],
}

# ── .stem.mp4 helpers ──────────────────────────────────────────────────────────

def _count_audio_tracks(path: str) -> int:
    """Use ffprobe to count how many audio tracks are in the file."""
    import subprocess, json as _json
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "a", path,
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    data = _json.loads(out)
    return len(data.get("streams", []))


def _read_stem_metadata(path: str) -> List[str]:
    """
    Extract stem names from the JSON metadata embedded in a .stem.mp4 using
    ffprobe.  Falls back to an empty list if metadata is absent or unreadable.

    NI encodes stem metadata in the 'iTunNORM' / 'com.apple.iTunes' tags,
    but the simpler approach is to look at the stream title tags directly.
    """
    import subprocess, json as _json
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "a", path,
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        streams = _json.loads(out).get("streams", [])
        names = []
        for s in streams:
            title = s.get("tags", {}).get("title", "").strip().lower()
            if title:
                names.append(title)
        # index 0 is the mix; 1+ are stems
        return names[1:] if len(names) > 1 else []
    except Exception:
        return []


def _extract_track_ffmpeg(
    path: str, track_index: int, sample_rate: int
) -> np.ndarray:
    """
    Use ffmpeg to extract a single audio track from an MP4 by index and
    return it as a (samples, 2) float32 numpy array (stereo).
    """
    import subprocess
    cmd = [
        "ffmpeg", "-v", "quiet",
        "-i", path,
        "-map", f"0:a:{track_index}",
        "-ac", "2",                         # force stereo
        "-ar", str(sample_rate),
        "-f", "f32le",                      # raw float32 little-endian PCM
        "-",                                # pipe to stdout
    ]
    raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    audio = np.frombuffer(raw, dtype=np.float32)
    # interleaved stereo → (samples, 2)
    audio = audio.reshape(-1, 2)
    return audio


def load_stem_mp4(
    path: str,
    stem_names: Optional[List[str]] = None,
    sample_rate: int = 44100,
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """
    Load a Native Instruments .stem.mp4 file using ffmpeg directly.

    Returns
    -------
    mixture  : np.ndarray  shape (samples, 2)  — track 0 (the full mix)
    stems    : dict { stem_name: np.ndarray(samples, 2) } — tracks 1+

    Parameters
    ----------
    path        : path to the .stem.mp4 file
    stem_names  : override stem names. If None, names are read from stream
                  title metadata; falls back to 'stem_1', 'stem_2', …
    sample_rate : target sample rate (default 44100)
    """
    n_tracks = _count_audio_tracks(path)
    if n_tracks < 2:
        raise ValueError(
            f"{path} has only {n_tracks} audio track(s). "
            "A .stem.mp4 needs at least 2 (mix + one stem)."
        )

    # Extract all tracks
    all_tracks = [
        _extract_track_ffmpeg(path, i, sample_rate) for i in range(n_tracks)
    ]
    mixture = all_tracks[0]
    stem_audio_list = all_tracks[1:]

    # Resolve stem names
    if stem_names is None:
        stem_names = _read_stem_metadata(path)

    n_stems = len(stem_audio_list)
    if not stem_names or len(stem_names) != n_stems:
        if stem_names and len(stem_names) != n_stems:
            print(
                f"  [warn] --stem-names has {len(stem_names)} name(s) but file "
                f"contains {n_stems} stem track(s). Using generic names."
            )
        stem_names = [f"stem_{i+1}" for i in range(n_stems)]

    stems = dict(zip(stem_names, stem_audio_list))
    return mixture, stems


def write_wav(audio: np.ndarray, path: str, sample_rate: int = 44100) -> None:
    """Write a (samples, channels) array to a WAV file."""
    sf.write(path, audio, sample_rate)

# ── Audio helpers ──────────────────────────────────────────────────────────────

def load_audio(path: str, sr: int = 44100) -> np.ndarray:
    """Load a WAV/FLAC/MP3 file and return a (samples, channels) float32 array."""
    audio, file_sr = librosa.load(path, sr=sr, mono=False)
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=0)   # mono → stereo
    return audio.T  # (samples, channels)


def to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert (samples, channels) → (samples,) by averaging channels."""
    return audio.mean(axis=1)


def match_length(ref: np.ndarray, est: np.ndarray) -> tuple:
    """Trim or zero-pad est to match ref length along axis 0."""
    r, e = ref.shape[0], est.shape[0]
    if e > r:
        est = est[:r]
    elif e < r:
        pad = np.zeros((r - e, est.shape[1]), dtype=est.dtype)
        est = np.vstack([est, pad])
    return ref, est


# ── Spleeter separation ────────────────────────────────────────────────────────

def separate(mixture_path: str, model: str, out_dir: str) -> dict:
    """
    Run Spleeter on *mixture_path* and return a dict
    {stem_name: np.ndarray(samples, channels)}.

    Stem names are discovered by scanning the output directory, so this works
    correctly for preset model strings, config.json paths, and any number of
    stems without relying on STEM_MAP.
    """
    from spleeter.separator import Separator

    separator = Separator(model)
    separator.separate_to_file(mixture_path, out_dir)

    track_name = Path(mixture_path).stem
    stem_dir = Path(out_dir) / track_name

    if not stem_dir.exists():
        raise FileNotFoundError(
            f"Spleeter output directory not found: {stem_dir}\n"
            f"Expected Spleeter to write stems under: {stem_dir}"
        )

    wav_files = sorted(stem_dir.glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(f"No WAV stems found in Spleeter output dir: {stem_dir}")

    stems = {f.stem: load_audio(str(f)) for f in wav_files}
    print(f"  Spleeter produced stems: {list(stems.keys())}")
    return stems


# ── BSS metrics ────────────────────────────────────────────────────────────────

def compute_bss_metrics(
    reference_stems: dict,
    estimated_stems: dict,
    sr: int = 44100,
) -> pd.DataFrame:
    """
    Compute SDR / SIR / SAR for every matching stem.

    Both dicts map stem_name → np.ndarray(samples, channels).
    Returns a DataFrame with one row per stem.
    """
    common = sorted(set(reference_stems) & set(estimated_stems))
    if not common:
        raise ValueError("No common stem names between reference and estimate.")

    # mir_eval expects (n_sources, n_samples) in mono
    ref_matrix = np.stack([to_mono(reference_stems[s]) for s in common])
    est_matrix = np.stack([to_mono(estimated_stems[s]) for s in common])

    # Align lengths
    min_len = min(ref_matrix.shape[1], est_matrix.shape[1])
    ref_matrix = ref_matrix[:, :min_len]
    est_matrix = est_matrix[:, :min_len]

    sdr, sir, sar, _ = mir_eval.separation.bss_eval_sources(
        ref_matrix, est_matrix, compute_permutation=False
    )

    rows = []
    for i, stem in enumerate(common):
        rows.append(
            {
                "stem": stem,
                "SDR": round(float(sdr[i]), 4),
                "SIR": round(float(sir[i]), 4),
                "SAR": round(float(sar[i]), 4),
            }
        )
    return pd.DataFrame(rows)


# ── Single .stem.mp4 evaluation ───────────────────────────────────────────────

def evaluate_stem_mp4(
    stem_mp4_path: str,
    model: str = "spleeter:4stems",
    stem_names: Optional[List[str]] = None,
    sample_rate: int = 44100,
) -> pd.DataFrame:
    """
    Full pipeline for a single .stem.mp4 file:
      1. Extract mixture (track 0) and reference stems (tracks 1+).
      2. Separate the mixture with Spleeter.
      3. Match estimated stems to references by name.
      4. Compute and return SDR / SIR / SAR.

    Parameters
    ----------
    stem_mp4_path : path to the .stem.mp4 file
    model         : Spleeter model string or path to a config.json
    stem_names    : override stem names (e.g. ['vocals','drums','bass','other'])
    sample_rate   : target sample rate
    """
    print(f"  Loading .stem.mp4: {Path(stem_mp4_path).name}")
    mixture_audio, reference = load_stem_mp4(
        stem_mp4_path, stem_names=stem_names, sample_rate=sample_rate
    )
    print(f"  Stems found in file: {list(reference.keys())}")

    with tempfile.TemporaryDirectory() as tmp:
        # Write mixture to a temp WAV so Spleeter can read it
        mix_wav = os.path.join(tmp, "mixture.wav")
        write_wav(mixture_audio, mix_wav, sample_rate)

        print(f"  Separating with {model} …")
        estimated = separate(mix_wav, model, tmp)

    df = compute_bss_metrics(reference, estimated)
    df.insert(0, "track", Path(stem_mp4_path).stem.replace(".stem", ""))
    return df


# ── Dataset (batch) evaluation — .stem.mp4 mode ───────────────────────────────

def evaluate_dataset_stem_mp4(
    dataset_dir: str,
    model: str = "spleeter:4stems",
    stem_names: Optional[List[str]] = None,
    sample_rate: int = 44100,
) -> pd.DataFrame:
    """
    Walk *dataset_dir*, find every *.stem.mp4 file, evaluate each one,
    and return a combined DataFrame.
    """
    files = sorted(Path(dataset_dir).glob("*.stem.mp4"))
    if not files:
        raise FileNotFoundError(f"No .stem.mp4 files found in {dataset_dir}")

    all_results = []
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Evaluating: {f.name}")
        try:
            df = evaluate_stem_mp4(
                str(f), model=model, stem_names=stem_names, sample_rate=sample_rate
            )
            all_results.append(df)
        except Exception as exc:
            print(f"  [error] Skipped {f.name}: {exc}")

    if not all_results:
        raise RuntimeError("All tracks failed evaluation.")
    return pd.concat(all_results, ignore_index=True)




def evaluate_track(
    mixture_path: str,
    stems_dir: str,
    model: str = "spleeter:2stems",
) -> pd.DataFrame:
    """
    Separate one mixture with Spleeter, compare to ground-truth stems in
    *stems_dir*, and return a metrics DataFrame.

    stems_dir must contain files named <stem_name>.wav (e.g. vocals.wav).
    """
    stem_names = STEM_MAP.get(model, STEM_MAP["spleeter:2stems"])

    # Load ground-truth
    reference = {}
    for stem in stem_names:
        candidate = Path(stems_dir) / f"{stem}.wav"
        if candidate.exists():
            reference[stem] = load_audio(str(candidate))
        else:
            print(f"  [warn] Ground-truth stem not found, skipping: {candidate}")

    if not reference:
        raise FileNotFoundError(f"No ground-truth stems found in {stems_dir}")

    # Separate
    with tempfile.TemporaryDirectory() as tmp:
        print(f"  Separating {Path(mixture_path).name} ...")
        estimated = separate(mixture_path, model, tmp)
        df = compute_bss_metrics(reference, estimated)

    df.insert(0, "track", Path(mixture_path).stem)
    return df


# ── Dataset (batch) evaluation ─────────────────────────────────────────────────

def evaluate_dataset(
    dataset_dir: str,
    model: str = "spleeter:2stems",
) -> pd.DataFrame:
    """
    Walk *dataset_dir*, find every track sub-folder containing mixture.wav,
    evaluate each one, and return a combined DataFrame.
    """
    dataset_path = Path(dataset_dir)
    track_dirs = sorted(
        d for d in dataset_path.iterdir()
        if d.is_dir() and (d / "mixture.wav").exists()
    )

    if not track_dirs:
        raise FileNotFoundError(
            f"No track folders with mixture.wav found in {dataset_dir}"
        )

    all_results = []
    for i, track_dir in enumerate(track_dirs, 1):
        print(f"[{i}/{len(track_dirs)}] Evaluating: {track_dir.name}")
        try:
            df = evaluate_track(
                mixture_path=str(track_dir / "mixture.wav"),
                stems_dir=str(track_dir),
                model=model,
            )
            all_results.append(df)
        except Exception as exc:
            print(f"  [error] Skipped {track_dir.name}: {exc}")

    if not all_results:
        raise RuntimeError("All tracks failed evaluation.")

    return pd.concat(all_results, ignore_index=True)


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    """Pretty-print per-stem averages and overall median."""
    print("\n" + "=" * 60)
    print("  EVALUATION SUMMARY")
    print("=" * 60)

    per_stem = (
        df.groupby("stem")[["SDR", "SIR", "SAR"]]
        .agg(["mean", "std"])
        .round(3)
    )
    print("\nPer-stem averages (mean ± std):\n")
    for stem in per_stem.index:
        sdr_m = per_stem.loc[stem, ("SDR", "mean")]
        sdr_s = per_stem.loc[stem, ("SDR", "std")]
        sir_m = per_stem.loc[stem, ("SIR", "mean")]
        sir_s = per_stem.loc[stem, ("SIR", "std")]
        sar_m = per_stem.loc[stem, ("SAR", "mean")]
        sar_s = per_stem.loc[stem, ("SAR", "std")]
        print(
            f"  {stem:<16}  SDR={sdr_m:+.2f}±{sdr_s:.2f}  "
            f"SIR={sir_m:+.2f}±{sir_s:.2f}  "
            f"SAR={sar_m:+.2f}±{sar_s:.2f}"
        )

    print(
        f"\n  Overall median   "
        f"SDR={df['SDR'].median():+.3f}  "
        f"SIR={df['SIR'].median():+.3f}  "
        f"SAR={df['SAR'].median():+.3f}"
    )
    print("=" * 60 + "\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Evaluate Spleeter separation quality (SDR / SIR / SAR).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stem-mp4",  help="Path to a single .stem.mp4 file (NI Stem format).")
    mode.add_argument("--mixture",   help="Path to a single mixture WAV file.")
    mode.add_argument("--dataset",   help="Path to a dataset folder (batch mode).")

    p.add_argument(
        "--stems",
        help="[--mixture mode] Folder containing ground-truth stem WAV files.",
    )
    p.add_argument(
        "--stem-mp4-batch",
        action="store_true",
        help="[--dataset mode] Treat dataset folder as a collection of .stem.mp4 files.",
    )
    p.add_argument(
        "--stem-names",
        nargs="+",
        metavar="NAME",
        help=(
            "Override stem names read from .stem.mp4 metadata.  "
            "Must match the number of stem tracks in the file.  "
            "Example: --stem-names vocals drums bass other"
        ),
    )
    p.add_argument(
        "--model",
        default="spleeter:2stems",
        help=(
            "Spleeter model string (e.g. spleeter:4stems) "
            "or path to a finetuned config.json."
        ),
    )
    p.add_argument(
        "--out",
        default="spleeter_eval_results.csv",
        help="Output CSV path for per-track / per-stem results.",
    )
    p.add_argument(
        "--sr",
        type=int,
        default=44100,
        help="Sample rate used when loading audio.",
    )
    return p


def main():
    args = build_parser().parse_args()

    if args.stem_mp4:
        print(f"\nSingle .stem.mp4 mode: {args.stem_mp4}")
        results = evaluate_stem_mp4(
            args.stem_mp4,
            model=args.model,
            stem_names=args.stem_names,
            sample_rate=args.sr,
        )
    elif args.mixture:
        if not args.stems:
            raise SystemExit("--stems is required when using --mixture.")
        print(f"\nSingle-track WAV mode: {args.mixture}")
        results = evaluate_track(args.mixture, args.stems, args.model)
    else:
        if args.stem_mp4_batch:
            print(f"\nBatch .stem.mp4 mode: {args.dataset}")
            results = evaluate_dataset_stem_mp4(
                args.dataset,
                model=args.model,
                stem_names=args.stem_names,
                sample_rate=args.sr,
            )
        else:
            print(f"\nBatch WAV mode: {args.dataset}")
            results = evaluate_dataset(args.dataset, args.model)

    print_summary(results)

    results.to_csv(args.out, index=False)
    print(f"Results saved to: {args.out}\n")
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()