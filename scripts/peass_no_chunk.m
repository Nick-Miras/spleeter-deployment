% ==========================================
% 1. CONFIGURATION
% ==========================================
addpath(genpath('scripts/peass-software'));

% NOTE: Populate wav_dataset_path with scripts/extract_musdb18_wavs.py
% before running this file, because MATLAB doesn't have a native MUSDB mp4 decoder.

wav_dataset_path = '.temp_wavs/test';
estimates_base_path = 'output';

% Only evaluate the first track
evaluate_first_track_only = false;

% The stem you want to evaluate
target_stem = 'other';

% All possible MUSDB stems
all_stems = {'vocals', 'drums', 'bass', 'other'};

% Directory for PEASS temporary calculation files
options.destDir = 'peass_temp_output/';
if ~exist(options.destDir, 'dir')
    mkdir(options.destDir);
end

options.segmentationFactor = 12; % Set to 1 to process the entire track at once (no chunking)

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
    estimate_file = fullfile(estimates_base_path, track_name, sprintf('%s.wav', target_stem));
    
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
    
    % Explicit memory cleanup before PEASS
    clear res;
    java.lang.Runtime.getRuntime().gc();
    
    try
        % Pass the full files directly instead of chunking
        res = PEASS_ObjectiveMeasure(reference_files, estimate_file, options);
        
        fprintf('  -> OPS (Overall):      %.2f\n', res.OPS);
        fprintf('  -> TPS (Target):       %.2f\n', res.TPS);
        fprintf('  -> IPS (Interference): %.2f\n', res.IPS);
        fprintf('  -> APS (Artifacts):    %.2f\n', res.APS);
        
        evaluated_count = evaluated_count + 1;
        ops_total = ops_total + res.OPS;
        tps_total = tps_total + res.TPS;
        ips_total = ips_total + res.IPS;
        aps_total = aps_total + res.APS;
        
    catch ME
        fprintf('  [Error] Failed to evaluate %s: %s\n', track_name, ME.message);
    end
    
    % Clean up temporary PEASS files
    if exist(options.destDir, 'dir')
        peass_files = dir(fullfile(options.destDir, '*'));
        peass_dirs = peass_files([peass_files.isdir] & ~ismember({peass_files.name}, {'.', '..'}));
        for d = 1:length(peass_dirs)
            rmdir(fullfile(options.destDir, peass_dirs(d).name), 's');
        end
        peass_reg_files = peass_files(~[peass_files.isdir]);
        for f = 1:length(peass_reg_files)
            delete(fullfile(options.destDir, peass_reg_files(f).name));
        end
    end
    
    if evaluate_first_track_only && evaluated_count >= 1
        fprintf('evaluate_first_track_only is true. Evaluated 1 track. Stopping.\n');
        break;
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
