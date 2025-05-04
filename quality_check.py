import os
import subprocess
import json
from fractions import Fraction
import sys
import concurrent.futures
import time
import threading # Added for locking the log file

# --- (get_video_info function remains the same as the robust version) ---
def get_video_info(video_path):
    # Reuse the robust get_video_info function from the previous version
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,r_frame_rate",
        "-of", "json", "-i", video_path
    ]
    # Increased timeout slightly, can be adjusted
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=45, check=False) # check=False to handle errors manually
    except subprocess.TimeoutExpired:
        print(f"⏰ Probe timed out: {os.path.basename(video_path)}", file=sys.stderr)
        return None # Indicate error

    if result.returncode != 0:
        error_msg = result.stderr.strip()
        print(f"❌ Probe error ({result.returncode}): {os.path.basename(video_path)} - {error_msg}", file=sys.stderr)
        return None # Indicate error

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"❌ JSON decode error: {os.path.basename(video_path)}", file=sys.stderr)
        return None # Indicate error

    # --- Safely get duration ---
    duration = None
    if "format" in data and "duration" in data["format"]:
        try:
            duration = float(data["format"]["duration"])
        except (ValueError, TypeError):
            # Log error but return None as it's critical info
            print(f"⚠️ Invalid duration format: {os.path.basename(video_path)}", file=sys.stderr)
            return None
    else:
        # Log error but return None as it's critical info
        print(f"⚠️ No duration found: {os.path.basename(video_path)}", file=sys.stderr)
        return None

    # --- Safely get FPS ---
    fps = None
    if "streams" in data:
        for stream in data["streams"]:
            if stream.get("codec_type") == "video" and "r_frame_rate" in stream:
                fps_str = stream["r_frame_rate"]
                if fps_str and fps_str != "0/0":
                    try:
                        fps = float(Fraction(*map(int, fps_str.split("/"))))
                        break # Found valid FPS
                    except (ValueError, ZeroDivisionError, TypeError):
                         print(f"⚠️ Invalid FPS format '{fps_str}': {os.path.basename(video_path)}", file=sys.stderr)
                else:
                     print(f"⚠️ Invalid FPS value '{fps_str}': {os.path.basename(video_path)}", file=sys.stderr)

    # --- Return results only if both duration and FPS are valid ---
    if duration is not None and fps is not None:
        return {
            "duration": duration,
            "fps": fps
        }
    elif duration is not None: # Duration found, but FPS wasn't
         print(f"⚠️ No valid FPS found (duration was {duration:.2f}s): {os.path.basename(video_path)}", file=sys.stderr)
         # Return None because FPS is required for filtering
         return None
    else: # Should be covered by earlier checks, but safety first
        return None
# --- (End of get_video_info) ---


def process_video(video_path, log_file_path, log_lock):
    """
    Worker function to process a single video file.
    Checks criteria, removes if needed, and logs the processed path.
    Returns: Tuple (status_string, video_path) e.g. ("kept", "/path/to/vid.mp4")
             status_string can be "kept", "removed", "error"
    """
    absolute_path = os.path.abspath(video_path)
    base_name = os.path.basename(video_path)
    status = "error"  # Default status

    try:
        info = get_video_info(video_path)

        if not info:
            print(f"🚫 Skipping (probe error/missing info): {base_name}")
            try:
                os.remove(video_path)
                print(f"🗑️ Removed (probe error/missing info): {base_name}")
                status = "removed"
            except OSError as e:
                print(f"❌ Error removing {base_name}: {e}", file=sys.stderr)
                status = "error"
        else:
            duration, fps = info["duration"], info["fps"]
            remove_reason = None
            if duration < 9.5 or duration > 10.5:
                remove_reason = f"Duration {duration:.2f}s"
            elif abs(fps-30) > 1:
                remove_reason = f"FPS {fps:.2f}"

            if remove_reason:
                try:
                    os.remove(video_path)
                    print(f"🗑️ Removed ({remove_reason}): {base_name}")
                    status = "removed"
                except OSError as e:
                    print(f"❌ Error removing {base_name}: {e}", file=sys.stderr)
                    status = "error"  # Failed to remove, count as error
            else:
                # Keep print concise for valid files during parallel runs
                status = "kept"

    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout processing: {base_name}", file=sys.stderr)
        try:
            os.remove(video_path)
            print(f"🗑️ Removed (timeout): {base_name}")
            status = "removed"
        except OSError as e:
            print(f"❌ Error removing {base_name}: {e}", file=sys.stderr)
            status = "error"

    except Exception as e:
        print(f"❌ Unexpected error processing {base_name}: {e}", file=sys.stderr)
        try:
            os.remove(video_path)
            print(f"🗑️ Removed (unexpected error): {base_name}")
            status = "removed"
        except OSError as e:
            print(f"❌ Error removing {base_name}: {e}", file=sys.stderr)
            status = "error"

    # --- Log regardless of status to prevent reprocessing ---
    try:
        with log_lock:  # Ensure only one thread writes at a time
            with open(log_file_path, 'a', encoding='utf-8') as log_f:
                log_f.write(absolute_path + '\n')
    except IOError as e:
        print(f"❌ CRITICAL: Failed to write to log file {log_file_path}: {e}", file=sys.stderr)

    return status, absolute_path


def load_processed_files(log_file_path):
    """Loads processed file paths from the log file into a set."""
    processed = set()
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    processed.add(line.strip())
        except IOError as e:
             print(f"⚠️ Warning: Could not read log file {log_file_path}: {e}", file=sys.stderr)
             # Continue with an empty set, processing might repeat
    return processed


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

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(process_video, path, log_file_path, log_lock): path
            for path in video_paths_to_process
        }

        try:
            for future in concurrent.futures.as_completed(future_to_path):
                original_path = future_to_path[future]
                try:
                    status, _ = future.result()
                    if status in results:
                        results[status] += 1
                    else:
                        print(f"⚠️ Unknown status '{status}' received for {os.path.basename(original_path)}", file=sys.stderr)
                        results["error"] += 1

                    # --- Progress Update Logic ---
                    completed_count += 1
                    # Update progress every N files or on the very last file
                    if completed_count % progress_update_interval == 0 or completed_count == total_to_process_this_run:
                        percent = (completed_count / total_to_process_this_run) * 100
                        # Use \r to return to beginning of line, pad with spaces to clear previous longer messages
                        progress_line = f"\rProgress: {completed_count} / {total_to_process_this_run} ({percent:.1f}%) completed. "
                        print(progress_line, end='', flush=True) # end='' prevents newline, flush forces output

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
