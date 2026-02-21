import os
import sys

# Enable High-Speed Transfers (Must be set before importing huggingface_hub components that use it)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

from huggingface_hub import HfApi, create_repo, upload_folder
from huggingface_hub.utils import HfHubHTTPError

def check_hf_transfer():
    try:
        import hf_transfer
        print("Success: hf_transfer is installed and enabled.")
    except ImportError:
        print("Error: hf_transfer is not installed.")
        print("Please run: pip install hf_transfer")
        sys.exit(1)

def upload_datasets():
    # Verification
    check_hf_transfer()

    # Configuration
    local_folder = os.path.join(os.getcwd(), "data", "Datasets")
    
    print("=== Hugging Face Dataset Uploader (Optimized for Large Files) ===")
    print(f"Uploading from: {local_folder}")
    
    # Get user input
    try:
        api = HfApi()
        user = api.whoami()
        username = user['name']
        print(f"Logged in as: {username}")
    except Exception:
        print("Error: You are not logged in. Please run 'huggingface-cli login' in your terminal first.")
        return

    repo_name = "qrowraven/Datasetqrow"
    print(f"Target repository: {repo_name}")

    # Create Repository
    print(f"\nChecking repository '{repo_name}'...")
    try:
        # Visibility Check: Ensure private=False
        create_repo(repo_name, repo_type="dataset", private=False, exist_ok=True)
        print("Repository checked (exists or created).")
    except Exception as e:
        print(f"Note: Repository creation check returned: {e}")
        # Continue anyway as it might just exist

    # Upload
    print("\nStarting upload... This may take a while depending on your internet connection.")
    try:
        upload_folder(
            folder_path=local_folder,
            repo_id=repo_name,
            repo_type="dataset",
            path_in_repo=".",  # Upload to root of repo
            commit_message="Upload datasets via automated script"
        )
        print(f"\nSuccess! Your datasets are available at: https://huggingface.co/datasets/{repo_name}")
    except Exception as e:
        print(f"\nUpload failed: {e}")

if __name__ == "__main__":
    upload_datasets()
