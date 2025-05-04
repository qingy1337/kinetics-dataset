#!/bin/bash
set -euo pipefail

# Root download directories
root_dl="k600"
root_dl_targz="k600_targz"

# Create directories if missing
mkdir -p "$root_dl" "$root_dl_targz"

# aria2 options: continue, 16 splits, 16 connections/server, 4 parallel downloads
ARIA2_OPTS="-c -s16 -x16 -j4 --input-file"

# Function to fetch URL lists and download via aria2
download_batch() {
  local list_url=$1
  local out_dir=$2

  # Prepare output directory
  mkdir -p "$out_dir"

  # Fetch URL list
  curl -sSL "$list_url" -o "${out_dir}/urls.txt"  # uses curl for simplicity

  # Invoke aria2
  aria2c $ARIA2_OPTS "${out_dir}/urls.txt" -d "$out_dir"
}

# Download train, val, test tarballs
download_batch "https://s3.amazonaws.com/kinetics/600/train/k600_train_path.txt" "$root_dl_targz/train"
download_batch "https://s3.amazonaws.com/kinetics/600/val/k600_val_path.txt"   "$root_dl_targz/val"
download_batch "https://s3.amazonaws.com/kinetics/600/test/k600_test_path.txt" "$root_dl_targz/test"

# Download annotation files individually (small files)
mkdir -p "$root_dl/annotations"
aria2c -c \
       https://s3.amazonaws.com/kinetics/600/annotations/train.txt \
       https://s3.amazonaws.com/kinetics/600/annotations/val.txt \
       https://s3.amazonaws.com/kinetics/600/annotations/test.csv \
       https://s3.amazonaws.com/kinetics/600/annotations/kinetics600_holdout_test.csv \
       -d "$root_dl/annotations"

# Download README
aria2c -c https://s3.amazonaws.com/kinetics/600/readme.md -d "$root_dl"

echo -e "\nDownloads complete! Now run extractor, k600_extractor.sh"
