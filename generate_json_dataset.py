import os
import json
from glob import glob

def generate_dataset_json(root_dir='.', output_file='dataset.json'):
    dataset = []
    
    # Get all directories in root_dir (each represents an action)
    actions = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    
    for action in actions:
        action_dir = os.path.join(root_dir, action)
        
        # Find all mp4 files in this action directory
        video_files = glob(os.path.join(action_dir, '*.mp4'))
        
        for video_path in video_files:
            # Create relative path from root_dir
            rel_path = os.path.relpath(video_path, root_dir)
            
            # Create caption by capitalizing the action name
            caption = action.capitalize()
            
            dataset.append({
                "video": rel_path.replace('\\', '/'),  # Use forward slashes for consistency
                "caption": caption
            })
    
    # Write to JSON file
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2)
    
    print(f"Dataset JSON file created at {output_file} with {len(dataset)} entries.")

# Example usage:
generate_dataset_json(root_dir='./', output_file='kinetics.json')
