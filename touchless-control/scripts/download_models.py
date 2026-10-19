"""Touchless Computer Control System - Model Download Script."""

import os
import sys
import urllib.request
from pathlib import Path

MODELS = {
    "hand_landmarker.task": {
        "url": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        "description": "MediaPipe Hand Landmarker Model (float16)"
    }
}


def download_file(url: str, dest_path: Path):
    """Downloads a file with progress reporting."""
    print(f"Downloading from {url}...")
    
    def reporthook(count, block_size, total_size):
        if total_size > 0:
            percent = int(count * block_size * 100 / total_size)
            downloaded_mb = (count * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\rProgress: {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")
            sys.stdout.flush()

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")
    
    try:
        urllib.request.urlretrieve(url, temp_path, reporthook=reporthook)
        print()  # Newline after progress
        if temp_path.exists():
            temp_path.replace(dest_path)
            print(f"Saved successfully: {dest_path}")
            return True
    except Exception as e:
        print(f"\nDownload failed: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False


def main():
    root_dir = Path(__file__).resolve().parent.parent
    models_dir = root_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Model Downloader ===")
    print(f"Destination: {models_dir}\n")

    for filename, info in MODELS.items():
        target = models_dir / filename
        if target.exists() and target.stat().st_size > 0:
            print(f"[FOUND] {info['description']} already exists at {target} ({target.stat().st_size / 1024 / 1024:.2f} MB). Skipping.")
            continue
        
        print(f"[FETCHING] {info['description']}")
        success = download_file(info["url"], target)
        if not success:
            print(f"Error: Failed to download {filename}.")
            sys.exit(1)

    print("\nAll required models downloaded successfully!")


if __name__ == "__main__":
    main()
