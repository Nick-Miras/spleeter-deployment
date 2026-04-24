% ==========================================
% 1. CONFIGURATION
% ==========================================
addpath(genpath('scripts/peass-software'));

% NOTE: This assumes MUSDB18 tracks are already extracted to WAV format 
% in wav_dataset_path, as MATLAB doesn't have a native MUSDB mp4 decoder.

wav_dataset_path = '.temp_wavs/test';
estimates_base_path = 'output';

% Only evaluate the first track
evaluate_first_track_only = false;

% The stem you want to evaluate
target_stem = 'vocals';

% All possible MUSDB stems
all_stems = {'vocals', 'drums', 'bass', 'other'};

% Directory for PEASS temporary calculation files
options.destDir = 'peass_temp_output/';
if ~exist(options.destDir, 'dir')
    mkdir(options.destDir);
end

% ==========================================
% 2. EVALUATE LOOP
% ==========================================
% Get all track directories in the test set
tracks = dir(wav_dataset_path);
tracks = tracks([tracks.isdir] & ~ismember({tracks.name}, {'.', '..'}));

fprintf('Found %d tracks in the test subset.\n', length(tracks));

evaluated_count = 0;
ops_total = 0;
tps_total = 0;
ips_total = 0;
aps_total = 0;

for i = 1:length(tracks)
    track_name = tracks(i).name;
    fprintf('\nProcessing: %s\n', track_name);
    
    track_wav_dir = fullfile(wav_dataset_path, track_name);
    target_wav_path = fullfile(track_wav_dir, sprintf('%s.wav', target_stem));
    
    if ~exist(target_wav_path, 'file')
        fprintf('  [Warning] Reference WAV not found at %s. Skipping.\n', target_wav_path);
        continue;
    end
    
    % Locate your model's estimate for this specific track
    estimate_file = fullfile(estimates_base_path, sprintf('%s.stem', track_name), sprintf('%s.wav', target_stem));
    
    if ~exist(estimate_file, 'file')
        fprintf('  [Warning] Estimate not found at %s. Skipping evaluation.\n', estimate_file);
        continue;
    end
    
    % Construct the reference cell array (Target MUST be first)
    reference_files = {target_wav_path};
    
    % Add the remaining stems as interferences
    for j = 1:length(all_stems)
        stem = all_stems{j};
        if ~strcmp(stem, target_stem)
            interf_path = fullfile(track_wav_dir, sprintf('%s.wav', stem));
            reference_files{end+1} = interf_path;
        end
    end
    
    fprintf('  Computing PEASS metrics...\n');
    try
        info = audioinfo(reference_files{1});
        fs = info.SampleRate;
        total_samples = info.TotalSamples;
        
        chunk_length_sec = 10;
        chunk_samples = chunk_length_sec * fs;
        
        num_chunks = ceil(total_samples / chunk_samples);
        
        ops_sum = 0; tps_sum = 0; ips_sum = 0; aps_sum = 0;
        
        for c = 1:num_chunks
            start_idx = (c-1)*chunk_samples + 1;
            end_idx = min(c*chunk_samples, total_samples);
            
            % Read chunks
            temp_refs = cell(size(reference_files));
            for ref_idx = 1:length(reference_files)
                [y, ~] = audioread(reference_files{ref_idx}, [start_idx, end_idx]);
                temp_filename = sprintf('peass_temp_output/ref_%d.wav', ref_idx);
                audiowrite(temp_filename, y, fs);
                temp_refs{ref_idx} = temp_filename;
            end
            
            [y_est, ~] = audioread(estimate_file, [start_idx, end_idx]);
            temp_est = 'peass_temp_output/est.wav';
            audiowrite(temp_est, y_est, fs);
            
            res = PEASS_ObjectiveMeasure(temp_refs, temp_est, options);
            ops_sum = ops_sum + res.OPS;
            tps_sum = tps_sum + res.TPS;
            ips_sum = ips_sum + res.IPS;
            aps_sum = aps_sum + res.APS;
        end
        
        ops_avg = ops_sum / num_chunks;
        tps_avg = tps_sum / num_chunks;
        ips_avg = ips_sum / num_chunks;
        aps_avg = aps_sum / num_chunks;
        
        fprintf('  -> OPS (Overall):      %.2f\n', ops_avg);
        fprintf('  -> TPS (Target):       %.2f\n', tps_avg);
        fprintf('  -> IPS (Interference): %.2f\n', ips_avg);
        fprintf('  -> APS (Artifacts):    %.2f\n', aps_avg);
        
        evaluated_count = evaluated_count + 1;
        ops_total = ops_total + ops_avg;
        tps_total = tps_total + tps_avg;
        ips_total = ips_total + ips_avg;
        aps_total = aps_total + aps_avg;
        if evaluate_first_track_only && evaluated_count >= 1
            fprintf('evaluate_first_track_only is true. Evaluated 1 track. Stopping.\n');
            break;
        end
        
    catch ME
        fprintf('  [Error] Failed to evaluate %s: %s\n', track_name, ME.message);
    end
end

if evaluated_count > 0
    fprintf('\nAverage PEASS across %d evaluated track(s):\n', evaluated_count);
    fprintf('  -> OPS (Overall):      %.2f\n', ops_total / evaluated_count);
    fprintf('  -> TPS (Target):       %.2f\n', tps_total / evaluated_count);
    fprintf('  -> IPS (Interference): %.2f\n', ips_total / evaluated_count);
    fprintf('  -> APS (Artifacts):    %.2f\n', aps_total / evaluated_count);
else
    fprintf('\nNo tracks were evaluated, so no average PEASS score could be computed.\n');
end
