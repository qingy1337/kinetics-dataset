import os
import subprocess
import json
from fractions import Fraction
import sys
import concurrent.futures
import time
import threading


def format_time(seconds):
    """Format time in seconds to a human-readable string."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins} min {secs} sec" if mins else f"{secs} sec"


# --- (get_video_info, process_video, load_processed_files remain the same) ---
def get_video_info(video_path):
    # ... (same as before) ...
    pass

def process_video(video_path, log_file_path, log_lock):
    # ... (same as before, including the abs(fps-30) > 1 check) ...
    # Make sure this function still includes your FPS check:
    # elif abs(fps-30) > 1:
    #     remove_reason = f"FPS {fps:.2f}"
    pass

def load_processed_files(log_file_path):
    # ... (same as before) ...
    pass


def filter_videos_parallel(root_dir, log_file_path=".processed_videos.log", max_workers=None):
    """
    Filters videos in parallel using ThreadPoolExecutor, supporting resume and progress display.
    """
    if max_workers is None:
        max_workers = min(os.cpu_count() * 2, 16)

    print(f"--- Starting resumable parallel video filtering in {root_dir} ---")
    print(f"Using log file: {log_file_path}")
    print(f"Max workers: {max_workers}")
    start_time = time.time()

    # 1. Load already processed files
    processed_files_set = load_processed_files(log_file_path)
    print(f"Loaded {len(processed_files_set)} paths from log file.")

    # 2. Collect video file paths *not* in the processed set
    video_paths_to_process = []
    total_files_found = 0
    for dirpath, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".mp4"):
                total_files_found += 1
                absolute_path = os.path.abspath(os.path.join(dirpath, file))
                if absolute_path not in processed_files_set:
                    video_paths_to_process.append(absolute_path)

    skipped_count = total_files_found - len(video_paths_to_process)
    total_to_process_this_run = len(video_paths_to_process) # Get total for progress %

    print(f"Found {total_files_found} total MP4 files.")
    if skipped_count > 0:
        print(f"Skipping {skipped_count} files already processed (found in log).")

    if not video_paths_to_process:
        print("No new videos to process.")
        return

    print(f"Processing {total_to_process_this_run} new files...")

    # 3. Use ThreadPoolExecutor
    results = {"kept": 0, "removed": 0, "error": 0}
    log_lock = threading.Lock()
    completed_count = 0 # <-- Initialize progress counter
    progress_update_interval = 50 # <-- How often to update the progress line
    total_processing_time = 0.0  # Track total time spent processing files

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(process_video, path, log_file_path, log_lock): path
            for path in video_paths_to_process
        }

        try:
            for future in concurrent.futures.as_completed(future_to_path):
                original_path = future_to_path[future]
                try:
                    status, duration = future.result()  # duration is time spent processing
                    if status in results:
                        results[status] += 1
                    else:
                        print(f"⚠️ Unknown status '{status}' received for {os.path.basename(original_path)}", file=sys.stderr)
                        results["error"] += 1

                    total_processing_time += duration  # Add duration to running total
                    completed_count += 1

                    # --- Progress Update Logic ---
                    if completed_count % progress_update_interval == 0 or completed_count == total_to_process_this_run:
                        percent = (completed_count / total_to_process_this_run) * 100
                        remaining_files = total_to_process_this_run - completed_count
                        avg_time_per_file = total_processing_time / completed_count if completed_count > 0 else 0
                        estimated_remaining_time = avg_time_per_file * remaining_files
                        formatted_remaining = format_time(estimated_remaining_time)
                        progress_line = f"\rProgress: {completed_count} / {total_to_process_this_run} ({percent:.1f}%) completed. Est. remaining: {formatted_remaining}"
                        print(progress_line, end='', flush=True)

                except Exception as exc:
                    print(f"\n❌ Exception for {os.path.basename(original_path)} during result retrieval: {exc}", file=sys.stderr)
                    results["error"] += 1
                    completed_count += 1 # Still count this as completed for progress %
                    # Also log this path as processed
                    try:
                        with log_lock:
                            with open(log_file_path, 'a', encoding='utf-8') as log_f:
                                log_f.write(os.path.abspath(original_path) + '\n')
                    except IOError as e:
                        print(f"❌ CRITICAL: Failed to write to log file after exception for {original_path}: {e}", file=sys.stderr)

        except KeyboardInterrupt:
            print("\n🛑 User interrupted. Shutting down workers...")
            sys.exit(1)

    # --- Final Cleanup ---
    print() # Print a newline to move cursor off the progress line before the summary

    end_time = time.time()
    print("\n--- Filtering Complete ---")
    print(f"Files processed in this run: {total_to_process_this_run}")
    print(f"  Kept:     {results['kept']}")
    print(f"  Removed:  {results['removed']}")
    print(f"  Errors:   {results['error']}")
    print(f"Total files skipped (already processed): {skipped_count}")
    print(f"Total time for this run: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    target_directory = "./train/train/"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, ".processed_videos.log")

    if not os.path.isdir(target_directory):
        print(f"❌ Error: Target directory not found: {target_directory}", file=sys.stderr)
        sys.exit(1)

    filter_videos_parallel(target_directory, log_file_path=log_file)
