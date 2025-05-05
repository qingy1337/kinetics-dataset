# Dataset Preparation for IV2 Retraining

### Downloading
```
> git clone https://github.com/qingy1337/kinetics-dataset.git
> cd kinetics-dataset
/kinetics-dataset > git pull
/kinetics-dataset > bash ./k600_downloader.sh
/kinetics-dataset > bash ./k600_extractor.sh
```

### Reorganizing into folders
```
> cd kinetics-dataset
/kinetics-dataset > mv k600_reorganize.py ./k600/
/kinetics-dataset > cd k600
/kinetics-dataset/k600 > python k600_reorganize annotations/train.txt
```

### Remove un-ideal actions
```
/kinetics-dataset > mv removed_actions.txt ./k600/
/kinetics-dataset > cd k600
/kinetics-dataset/k600 > grep -v '^$' removed_actions.txt | tr '\n' '\0' | xargs -0 -I {} rm -rf "./train/train/{}/"
```

### Filter only quality videos (~30 fps, ~10 seconds in duration)
```
/kinetics-dataset > mv quality_check.py ./k600/
/kinetics-dataset > cd k600
/kinetics-dataset/k600 > python quality_check.py
```

### Generate JSON dataset (compatible with IV2 training)
```
/kinetics-dataset > mv generate_json_dataset.py ./k600/train/train/
/kinetics-dataset > cd k600/train/train/
/kinetics-dataset/k600/train/train > python generate_json_dataset.py # output saved to kinetics.json in /kinetics-dataset/k600/train/train/
```
