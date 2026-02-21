import os
from pathlib import Path

def rename_datasets(root_dir):
    root_path = Path(root_dir).resolve()
    if not root_path.exists():
        print(f"Directory {root_path} does not exist.")
        return

    print(f"Scanning {root_path}...")

    # Iterate over each dataset folder (Db1, Db3, etc.)
    for dataset_dir in root_path.iterdir():
        if not dataset_dir.is_dir():
            continue
            
        print(f"Processing dataset folder: {dataset_dir.name}")
        
        # Get all song folders
        all_folders = [f for f in dataset_dir.iterdir() if f.is_dir()]
        
        # Identify already renamed folders and their indices
        used_indices = set()
        renamed_folders = []
        unrenamed_folders = []
        
        for folder in all_folders:
            name = folder.name
            if name.startswith("Db_") and name[3:].isdigit():
                try:
                    idx = int(name[3:])
                    used_indices.add(idx)
                    renamed_folders.append(folder)
                except ValueError:
                    unrenamed_folders.append(folder)
            else:
                unrenamed_folders.append(folder)
        
        # Sort unrenamed folders for deterministic ordering
        unrenamed_folders.sort(key=lambda x: x.name)
        
        print(f"Found {len(unrenamed_folders)} unrenamed folders in {dataset_dir.name}")
        
        # Rename unrenamed folders using lowest available indices
        current_idx = 0
        for song_folder in unrenamed_folders:
            # Find next available index
            while current_idx in used_indices:
                current_idx += 1
            
            original_name = song_folder.name
            new_name = f"Db_{current_idx:03d}"
            new_path = dataset_dir / new_name
            
            print(f"Renaming '{original_name}' to '{new_name}'")
            
            # Mark this index as used for next iterations
            used_indices.add(current_idx)
            
            txt_file = song_folder / "song_name.txt"
            try:
                with open(txt_file, "w", encoding="utf-8") as f:
                    f.write(original_name)
            except Exception as e:
                print(f"Error writing txt file for {original_name}: {e}")
                continue
                
            try:
                song_folder.rename(new_path)
            except Exception as e:
                print(f"Error renaming {original_name}: {e}")

if __name__ == "__main__":
    rename_datasets("Datasets")
