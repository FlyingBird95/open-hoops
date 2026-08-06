# Basketball YOLO Training

Fine-tune YOLO11x for basketball-specific detection.

## Classes

- `ball` — basketball
- `player` — on-court players
- `hoop` — rim/backboard
- `referee` — officials

## Setup

```bash
pip install roboflow
export ROBOFLOW_API_KEY=your_key_here
```

## Train

```bash
python -m open_hoops.training.train --epochs 50
```

## Evaluate

```bash
python -m open_hoops.training.evaluate --model basketball-yolo11x.pt
```

## Output

Training produces `basketball-yolo11x.pt` in the project root.
The detector automatically uses this model if present.
