import os
import argparse
import numpy as np
from spleeter.separator import Separator

try:
    import mir_eval
except ImportError:
    print("mir_eval is required. pip install mir_eval")
    exit(1)

try:
    import musdb
except ImportError:
    print("musdb is required to read .stem.mp4 files. pip install musdb stempeg")
    exit(1)

def evaluate_track(separator, track, instruments):
    """
    Evaluates a single musdb track containing 'audio' (mixture) and 'targets'
    """
    print(f"Processing track: {track.name} ...")
    
    # Perform separation directly on the track's audio numpy array (shape: n_samples, 2)
    # Spleeter's separate() handles numpy arrays seamlessly
    prediction = separator.separate(track.audio)

    reference_sources = []
    estimated_sources = []
    
    # Load ground truths and align with predictions
    for instrument in instruments:
        if instrument not in track.targets:
            print(f"Warning: Ground truth {instrument} not found in track {track.name}. Skipping instrument.")
            continue
            
        truth_audio = track.targets[instrument].audio
        est_audio = prediction[instrument]
        
        # Ensure length mismatch doesn't break evaluation
        min_len = min(len(truth_audio), len(est_audio))
        
        # Convert to mono for evaluation efficiency
        truth_mono = np.mean(truth_audio[:min_len], axis=1)
        est_mono = np.mean(est_audio[:min_len], axis=1)
        
        reference_sources.append(truth_mono)
        estimated_sources.append(est_mono)
        
    if not len(reference_sources):
        return None

    reference_sources = np.array(reference_sources)
    estimated_sources = np.array(estimated_sources)
    
    # Compute SDR, SIR, SAR, PERM
    sdr, sir, sar, _ = mir_eval.separation.bss_eval_sources(reference_sources, estimated_sources, False)
    
    results = {}
    for i, instrument in enumerate(instruments):
        results[instrument] = {
            'SDR': sdr[i],
            'SIR': sir[i],
            'SAR': sar[i]
        }
        
    return results

def main(config_path, dataset_dir, instruments, first_only=False):
    print(f"Loading Spleeter separator with config/model: {config_path}")
    separator = Separator(config_path)
    
    print(f"Loading musdb18 dataset from: {dataset_dir}")
    # Load test subset directly from .stem.mp4 files
    db = musdb.DB(root=dataset_dir, subsets=['test'], is_wav=False)
    
    if len(db) == 0:
        print(f"No tracks found in test set at {dataset_dir}.")
        return
        
    all_results = {inst: {'SDR': [], 'SIR': [], 'SAR': []} for inst in instruments}
    
    tracks_to_eval = db.tracks[:1] if first_only else db.tracks
    
    for track in tracks_to_eval:
        metrics = evaluate_track(separator, track, instruments)
        if metrics:
            for inst in instruments:
                if inst in metrics:
                    all_results[inst]['SDR'].append(metrics[inst]['SDR'])
                    all_results[inst]['SIR'].append(metrics[inst]['SIR'])
                    all_results[inst]['SAR'].append(metrics[inst]['SAR'])
                
    print("\n" + "="*40)
    print("OVERALL MEDIAN EVALUATION RESULTS")
    print("="*40)
    for inst in instruments:
        print(f"\n{inst.upper()}:")
        for metric in ['SDR', 'SIR', 'SAR']:
            if all_results[inst][metric]:
                med_val = np.median(all_results[inst][metric])
                print(f"  {metric}: {med_val:.3f} dB")
            else:
                print(f"  {metric}: N/A")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Custom evaluation script for spleeter using musdb18 .stem.mp4 files")
    parser.add_argument("--config", "-c", type=str, default="spleeter:4stems")
    parser.add_argument("--dataset_dir", "-d", type=str, required=True, 
                        help="Path to ROOT directory of musdb18 (must contain train/ and test/ folders)")
    parser.add_argument("--instruments", "-i", type=str, nargs='+', default=['vocals', 'drums', 'bass', 'other'])
    parser.add_argument("--first_only", action="store_true", 
                        help="Only evaluate the very first song in the test dataset to speed up evaluation")
    
    args = parser.parse_args()
    main(args.config, args.dataset_dir, args.instruments, args.first_only)