import os
import subprocess
import json
from fractions import Fraction
import sys # Added for printing to stderr

def get_video_info(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,r_frame_rate", # Ensure we request codec_type too
        "-of", "json", "-i", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"❌ Error probing {video_path}: {result.stderr.strip()}", file=sys.stderr)
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"❌ Error decoding JSON for {video_path}: {result.stdout}", file=sys.stderr)
        return None

    # --- Safely get duration ---
    duration = None
    if "format" in data and "duration" in data["format"]:
        try:
            duration = float(data["format"]["duration"])
        except (ValueError, TypeError):
            print(f"⚠️ Warning: Invalid duration format for {video_path}", file=sys.stderr)
            return None # Cannot proceed without duration
    else:
        print(f"⚠️ Warning: Could not find duration for {video_path}", file=sys.stderr)
        return None # Cannot proceed without duration

    # --- Safely get FPS from the first valid video stream ---
    fps = None
    if "streams" in data:
        for stream in data["streams"]:
            # Check if it's a video stream AND has frame rate info
            if stream.get("codec_type") == "video" and "r_frame_rate" in stream:
                fps_str = stream["r_frame_rate"]
                # Check for valid frame rate string (not "0/0" or empty)
                if fps_str and fps_str != "0/0":
                    try:
                        # Use Fraction for accurate FPS calculation
                        fps = float(Fraction(*map(int, fps_str.split("/"))))
                        # Found valid FPS, stop searching streams
                        break
                    except (ValueError, ZeroDivisionError, TypeError):
                        print(f"⚠️ Warning: Invalid r_frame_rate format '{fps_str}' in {video_path}", file=sys.stderr)
                        # Continue searching other streams if any
                else:
                     print(f"⚠️ Warning: Found video stream but invalid r_frame_rate '{fps_str}' in {video_path}", file=sys.stderr)
                     # Continue searching other streams if any

    if duration is not None and fps is not None:
        return {
            "duration": duration,
            "fps": fps
        }
    elif duration is not None:
         print(f"⚠️ Warning: Found duration but no valid FPS for {video_path}", file=sys.stderr)

    # If no valid video stream with FPS was found or duration was missing
    return None

def filter_videos(root_dir):
    print(f"--- Starting video filtering in {root_dir} ---")
    processed_count = 0
    removed_count = 0
    valid_count = 0

    for dirpath, _, files in os.walk(root_dir):
        for file in files:
            # Process only .mp4 files
            if file.lower().endswith(".mp4"):
                processed_count += 1
                video_path = os.path.join(dirpath, file)
                print(f"🔍 Analyzing [{processed_count}]: {video_path}")

                info = get_video_info(video_path)

                # If ffprobe failed or couldn't extract necessary info
                if not info:
                    print(f"🚫 Skipping due to probe error or missing info: {os.path.basename(video_path)}")
                    # Decide if you want to REMOVE files that ffprobe fails on
                    # Uncomment below to remove them:
                    # try:
                    #     os.remove(video_path)
                    #     print(f"🗑️ Removed due to probe error: {os.path.basename(video_path)}")
                    #     removed_count += 1
                    # except OSError as e:
                    #     print(f"❌ Error removing {video_path}: {e}", file=sys.stderr)
                    continue # Skip to the next file

                duration, fps = info["duration"], info["fps"]

                # --- Apply Filters ---
                remove_reason = None
                if duration < 9.5 or duration > 10.5:
                    remove_reason = f"Duration mismatch ({duration:.2f}s ≠ 10s ± 0.5s)"
                elif fps < 30:
                   remove_reason = f"FPS too low ({fps:.2f} < 30)"

                # --- Perform Action ---
                if remove_reason:
                    print(f"      Reason: {remove_reason}")
                    try:
                        os.remove(video_path)
                        print(f"🗑️ Removed: {os.path.basename(video_path)}")
                        removed_count += 1
                    except OSError as e:
                         print(f"❌ Error removing {video_path}: {e}", file=sys.stderr)
                else:
                    print(f"✅ Keeping ({duration:.2f}s, {fps:.2f} FPS): {os.path.basename(video_path)}")
                    valid_count += 1

    print("\n--- Filtering Complete ---")
    print(f"Total files processed: {processed_count}")
    print(f"Files kept: {valid_count}")
    print(f"Files removed: {removed_count}")
    print(f"Files skipped due to errors: {processed_count - valid_count - removed_count}")


if __name__ == "__main__":
    target_directory = "./train/train/"
    if not os.path.isdir(target_directory):
        print(f"❌ Error: Target directory not found: {target_directory}", file=sys.stderr)
        sys.exit(1) # Exit with an error code
    filter_videos(target_directory)
