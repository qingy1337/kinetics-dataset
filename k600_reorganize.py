import os
import shutil
import sys
import json

def parse_txt_to_json(txt_path):
    """Parse a .txt file into a JSON dict structure."""
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]

    sections = []
    current_section = []

    for line in lines:
        if line:
            current_section.append(line)
        else:
            if current_section:
                sections.append(current_section)
                current_section = []

    if current_section:
        sections.append(current_section)

    result = {}

    for section in sections:
        if not section:
            continue

        tag_line = section[0]
        tag = tag_line.rstrip(':')
        content = section[1:]

        result[tag] = content

    return result

def organize_files(json_data, base_dir):
    """Organize files into directories based on JSON data."""
    os.makedirs(base_dir, exist_ok=True)

    for key in json_data:
        if key == "train":
            continue

        dir_path = os.path.join(base_dir, key)
        os.makedirs(dir_path, exist_ok=True)

        for file_name in json_data[key]:
            src = os.path.join(base_dir, file_name)
            dst = os.path.join(dir_path, file_name)

            if not os.path.exists(src):
                print(f"⚠️ File not found: {src}. Skipping.")
                continue

            try:
                shutil.move(src, dst)
                print(f"✅ Moved: {src} → {dst}")
            except Exception as e:
                print(f"❌ Error moving {src}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python organize_videos.py <input.txt>")
        return

    input_txt = sys.argv[1]
    output_json = "structure.json"
    base_dir = "./train"

    # Step 1: Parse .txt into JSON
    print("Parsing input file...")
    json_data = parse_txt_to_json(input_txt)

    print(f"Got {len(json_data.keys())} categories!")

    # Step 2: Organize files
    print("Organizing files into directories...")
    organize_files(json_data, base_dir)
    print("✅ Done!")

if __name__ == "__main__":
    main()
