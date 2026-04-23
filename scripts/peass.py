import os
import musdb
import soundfile as sf
import numpy as np
import concurrent.futures
import uuid
import shutil
import multiprocessing
from pyass.peass import PEASS_ObjectiveMeasure

def process_single_chunk(start, end, reference_files, estimate_file, sr, peass_options):
    uid = str(uuid.uuid4())
    
    # Create a unique destDir for this chunk to avoid internal temp file collisions
    chunk_peass_options = peass_options.copy()
    chunk_dest_dir = os.path.join(peass_options['destDir'], uid)
    os.makedirs(chunk_dest_dir, exist_ok=True)
    chunk_peass_options['destDir'] = chunk_dest_dir
    
    # Read all arrays first to find the minimum length
    ref_arrays = []
    for i, ref_file in enumerate(reference_files):
        data, _ = sf.read(ref_file, start=start, frames=(end-start))
        ref_arrays.append(data)
        
    est_chunk, _ = sf.read(estimate_file, start=start, frames=(end-start))
    
    # Truncate to the shortest array to avoid broadcast errors
    min_len = min([len(est_chunk)] + [len(r) for r in ref_arrays])
    
    temp_refs = []
    for i, data in enumerate(ref_arrays):
        truncated_data = data[:min_len]
        temp_ref_path = f".temp_chunk_ref_{i}_{uid}.wav"
        sf.write(temp_ref_path, truncated_data, sr)
        temp_refs.append(temp_ref_path)
    
    est_chunk = est_chunk[:min_len]
    temp_est_path = f".temp_chunk_est_{uid}.wav"
    sf.write(temp_est_path, est_chunk, sr)
    
    # Calculate PEASS for the chunk
    chunk_scores = PEASS_ObjectiveMeasure(temp_refs, temp_est_path, chunk_peass_options)
    
    # Cleanup temp files and the unique PEASS destDir
    for path in temp_refs + [temp_est_path]:
        if os.path.exists(path):
            os.remove(path)
    shutil.rmtree(chunk_dest_dir, ignore_errors=True)
    
    return chunk_scores


def compute_peass_in_chunks(reference_files, estimate_file, peass_options, chunk_duration_sec=10):
    # Read the estimate file to get the samplerate and total length
    # Note: Using info to avoid loading the whole file if possible
    info = sf.info(estimate_file)
    sr = info.samplerate
    total_frames = info.frames
    chunk_frames = int(chunk_duration_sec * sr)
    
    ops_scores, tps_scores, ips_scores, aps_scores = [], [], [], []
    
    tasks = []
    # Collect chunk coordinates
    for start in range(0, total_frames, chunk_frames):
        end = min(start + chunk_frames, total_frames)
        if end - start == 0:
            break
        tasks.append((start, end))
            
    total_chunks = len(tasks)
    # Reduced to 5 to avoid Out-Of-Memory (OOM) stalls. PEASS is highly memory-intensive,
    # and running 10 parallel instances likely exhausts system RAM, causing severe disk swapping.
    max_workers = min(5, multiprocessing.cpu_count()) 
    print(f"    -> Dispatching {total_chunks} chunks to {max_workers} parallel workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_single_chunk, start, end, reference_files, estimate_file, sr, peass_options)
            for start, end in tasks
        ]
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            print(f"    -> Completed chunk {i + 1}/{total_chunks}...")
            chunk_scores = future.result()
            ops_scores.append(chunk_scores['OPS'])
            tps_scores.append(chunk_scores['TPS'])
            ips_scores.append(chunk_scores['IPS'])
            aps_scores.append(chunk_scores['APS'])

    # Return averaged scores
    return {
        'OPS': np.mean(ops_scores) if ops_scores else 0,
        'TPS': np.mean(tps_scores) if tps_scores else 0,
        'IPS': np.mean(ips_scores) if ips_scores else 0,
        'APS': np.mean(aps_scores) if aps_scores else 0
    }

def main():
    # ==========================================
    # 1. CONFIGURATION
    # ==========================================
    mp4_dataset_path = "data/musdb18" 
    wav_dataset_path = ".temp_wavs"
    
    # Path to your model's predictions (e.g., Spleeter outputs)
    estimates_base_path = "output" # TODO: Compute Output
    
    # The stem you want to evaluate
    target_stem = "vocals" 
    
    # All possible MUSDB stems
    all_stems = ["vocals", "drums", "bass", "other"]
    
    # Directory for PEASS temporary calculation files
    peass_options = {'destDir': './peass_temp_output/'}
    os.makedirs(peass_options['destDir'], exist_ok=True)

    # ==========================================
    # 2. INITIALIZE DATASET
    # ==========================================
    print("Loading MP4 dataset...")
    mus = musdb.DB(root=mp4_dataset_path, is_wav=False, subsets="test")
    print(f"Found {len(mus)} tracks in the test subset.")
    
    # ==========================================
    # 3. DECODE & EVALUATE LOOP
    # ==========================================
    for track in mus:
        print(f"\nProcessing: {track.name}")
        
        # --- Decode Step ---
        track_wav_dir = os.path.join(wav_dataset_path, track.subset, track.name)
        os.makedirs(track_wav_dir, exist_ok=True)
        
        target_wav_path = os.path.join(track_wav_dir, f"{target_stem}.wav")
        
        # Only decode if the WAV files don't already exist from a previous run
        if not os.path.exists(target_wav_path):
            print("  Decoding MP4 to WAV...")
            # Save mixture
            sf.write(os.path.join(track_wav_dir, 'mixture.wav'), track.audio, track.rate)
            # Save stems
            for stem_name, stem_data in track.targets.items():
                sf.write(os.path.join(track_wav_dir, f'{stem_name}.wav'), stem_data.audio, track.rate)
        else:
            print("  WAV files already exist. Skipping decode.")

        # --- Evaluate Step ---
        # Locate your model's estimate for this specific track
        estimate_file = os.path.join(estimates_base_path, track.name + '.stem', f"{target_stem}.wav")
        
        if not os.path.exists(estimate_file):
            print(f"  [Warning] Estimate not found at {estimate_file}. Skipping evaluation.")
            continue

        # Construct the reference list (Target MUST be first)
        reference_files = [target_wav_path]
        
        # Add the remaining stems as interferences
        for stem in all_stems:
            if stem != target_stem:
                interf_path = os.path.join(track_wav_dir, f"{stem}.wav")
                reference_files.append(interf_path)

        print("  Computing PEASS metrics in chunks...")
        try:
            peass_scores = compute_peass_in_chunks(reference_files, estimate_file, peass_options, chunk_duration_sec=10)
            
            print(f"  -> OPS (Overall):      {peass_scores['OPS']:.2f}")
            print(f"  -> TPS (Target):       {peass_scores['TPS']:.2f}")
            print(f"  -> IPS (Interference): {peass_scores['IPS']:.2f}")
            print(f"  -> APS (Artifacts):    {peass_scores['APS']:.2f}")
            
        except Exception as e:
            print(f"  [Error] Failed to evaluate {track.name}: {e}")


if __name__ == "__main__":
    main()
