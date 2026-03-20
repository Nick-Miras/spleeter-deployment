import os
import argparse
import numpy as np
import concurrent.futures
from spleeter.separator import Separator
import multiprocessing

try:
    import mir_eval
except ImportError:
    print("mir_eval is required. pip install mir_eval")
    exit(1)

try:
    import musdb
except ImportError:
    print("musdb is required. pip install musdb stempeg")
    exit(1)


def calculate_metrics_worker(track_name, reference_sources, estimated_sources, instruments):
    """
    Pure CPU function to calculate SDR, SIR, SAR. 
    Runs entirely isolated in a worker process.
    """
    # Compute SDR, SIR, SAR
    sdr, sir, sar, _ = mir_eval.separation.bss_eval_sources(
        np.array(reference_sources), 
        np.array(estimated_sources), 
        False
    )
    
    results = {}
    for i, instrument in enumerate(instruments):
        results[instrument] = {
            'SDR': sdr[i],
            'SIR': sir[i],
            'SAR': sar[i]
        }
        
    print(f"  -> Finished math for: {track_name}")
    return track_name, results


def main(config_path, dataset_dir, instruments, first_only=False):
    print(f"Loading Spleeter separator with config: {config_path}")
    separator = Separator(config_path)
    
    print(f"Loading musdb18 dataset from: {dataset_dir}")
    db = musdb.DB(root=dataset_dir, subsets=['test'], is_wav=False)
    
    if len(db) == 0:
        print(f"No tracks found in test set at {dataset_dir}.")
        return
        
    tracks_to_eval = db.tracks[:1] if first_only else db.tracks
    
    # Determine optimal number of CPU cores to use
    cpu_cores = os.cpu_count() or 4
    print(f"Starting Process Pool with {cpu_cores} background workers...\n")
    
    all_results = {inst: {'SDR': [], 'SIR': [], 'SAR': []} for inst in instruments}
    
    # Initialize Process Pool for CPU-heavy math
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu_cores) as executor:
        futures = []
        
        for track in tracks_to_eval:
            print(f"Isolating track on GPU: {track.name} ...")
            
            # 1. Force float32 and contiguous memory for TensorFlow safety
            audio_input = np.ascontiguousarray(track.audio, dtype=np.float32)
            
            # 2. Run separation (Fast, utilizes GPU)
            prediction = separator.separate(audio_input)
            
            reference_sources = []
            estimated_sources = []
            valid_instruments = []
            
            # 3. Prep data for the CPU workers
            for instrument in instruments:
                if instrument not in track.targets:
                    continue
                    
                truth_audio = track.targets[instrument].audio
                est_audio = prediction[instrument]
                
                # Align lengths and convert to mono for faster evaluation
                min_len = min(len(truth_audio), len(est_audio))
                truth_mono = np.mean(truth_audio[:min_len], axis=1)
                est_mono = np.mean(est_audio[:min_len], axis=1)
                
                reference_sources.append(truth_mono)
                estimated_sources.append(est_mono)
                valid_instruments.append(instrument)
                
            if reference_sources:
                # 4. Hand off the heavy math to a background CPU worker
                future = executor.submit(
                    calculate_metrics_worker, 
                    track.name, 
                    reference_sources, 
                    estimated_sources, 
                    valid_instruments
                )
                futures.append(future)

        print("\nAll tracks processed by GPU. Waiting for CPU workers to finish math...\n")
        
        # 5. Collect results as they finish
        for future in concurrent.futures.as_completed(futures):
            track_name, metrics = future.result()
            for inst in metrics:
                all_results[inst]['SDR'].append(metrics[inst]['SDR'])
                all_results[inst]['SIR'].append(metrics[inst]['SIR'])
                all_results[inst]['SAR'].append(metrics[inst]['SAR'])

    # --- Print Final Medians ---
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
    multiprocessing.set_start_method('spawn', force=True)
    
    parser = argparse.ArgumentParser(description="Parallel evaluation script for Spleeter")
    parser.add_argument("--config", "-c", type=str, default="spleeter:4stems")
    parser.add_argument("--dataset_dir", "-d", type=str, required=True)
    parser.add_argument("--instruments", "-i", type=str, nargs='+', default=['vocals', 'drums', 'bass', 'other'])
    parser.add_argument("--first_only", action="store_true")
    
    args = parser.parse_args()
    main(args.config, args.dataset_dir, args.instruments, args.first_only)