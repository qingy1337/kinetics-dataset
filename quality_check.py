import os
import subprocess
import json
from fractions import Fraction

def get_video_info(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=r_frame_rate", "-of", "json", "-i", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error probing {video_path}: {result.stderr}")
        return None

    data = json.loads(result.stdout)
    
    # Get duration (in seconds)
    duration = float(data["format"]["duration"])
    
    # Get FPS (from video stream)
    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            fps_str = stream["r_frame_rate"]
            fps = float(Fraction(*map(int, fps_str.split("/"))))
            return {
                "duration": duration,
                "fps": fps
            }
    
    return None  # No video stream found

def filter_videos(root_dir):
    for dirpath, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".mp4"):
                video_path = os.path.join(dirpath, file)
                print(f"🔍 Analyzing: {video_path}")
                info = get_video_info(video_path)
                if not info:
                    print(f"🚫 Skipping invalid video: {video_path}")
                    continue
                duration, fps = info["duration"], info["fps"]
                if duration < 9.5 or duration > 10.5:
                    print(f"⏱️  Duration mismatch ({duration:.2f}s ≠ 10s): {video_path}")
                    os.remove(video_path)
                elif fps < 30:
                    print(f"📉 FPS too low ({fps:.2f} < 30): {video_path}")
                    os.remove(video_path)
                else:
                    print(f"✅ Valid video: {video_path}")
    print("✅ Filtering complete!")

if __name__ == "__main__":
    filter_videos("./train/train/")
