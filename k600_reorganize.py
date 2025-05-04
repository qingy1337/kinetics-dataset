import os
import json
import shutil
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_json.json>")
        return

    input_json = sys.argv[1]
    base_dir = "./train"

    # Ensure the base directory exists
    os.makedirs(base_dir, exist_ok=True)

    # Load JSON data
    with open(input_json, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # Iterate over all keys in the JSON (except "train")
    for key in json_data:
        if key == "train":
            continue  # Skip the "train" key

        # Construct the target directory path
        dir_path = os.path.join(base_dir, key)
        os.makedirs(dir_path, exist_ok=True)

        # Process each file listed under the key
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

if __name__ == "__main__":
    main()
