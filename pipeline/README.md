# Face-to-Quori pipeline

This directory contains the experimental text-to-face retargeting pipeline:

```text
text prompt -> Stable Diffusion image -> MediaPipe landmarks
            -> normalized expression features -> Quori controls
```

## Generate a face

Run Stable Diffusion with the pipeline virtual environment. Do not use plain
`python3`, because the macOS system interpreter does not contain PyTorch and
Diffusers:

```bash
cd /Users/tuhinadas/vizij-web
pipeline/.venv/bin/python pipeline/generate_face.py \
  "a happy smiling face with raised cheeks"
```

The generated PNG is saved under `pipeline/outputs/gen_images/`.

## Extract landmarks and features

Use the pipeline virtual environment:

```bash
pipeline/.venv/bin/python pipeline/extract_features.py \
  pipeline/outputs/gen_images/extremely_evil_grin.png \
  --output pipeline/outputs/gen_images/extremely_evil_grin.features.json \
  --overlay pipeline/outputs/gen_images/extremely_evil_grin.landmarks.png
```

Always use `pipeline/.venv/bin/python` for this step. Plain `python3` uses
the system interpreter and does not include OpenCV or MediaPipe.

## Generate several expressions

Stable Diffusion is loaded once and then reused for every expression:

```bash
pipeline/.venv/bin/python pipeline/generate_faces.py \
  --file pipeline/expressions.txt
```

You can also provide prompts directly:

```bash
pipeline/.venv/bin/python pipeline/generate_faces.py \
  "neutral" \
  "happy smiling face with raised cheeks" \
  "sad pouty face with tears" \
  "angry face with sharply furrowed brows"
```

Each prompt produces a separate PNG in `pipeline/outputs/gen_images/`.
The `--seed` value is incremented for each prompt so the images are
reproducible but not identical. Use `--steps`, `--width`, and `--height` to
control generation cost and resolution.

The feature document contains all 478 normalized MediaPipe landmarks, the
MediaPipe semantic face-blendshape scores, and a small stable feature
vocabulary. Brow features now use MediaPipe's `browDown`, `browInnerUp`, and
`browOuterUp` scores so inner and outer brow movement can be mapped separately.
The vocabulary includes mouth opening, smile, frown, eye openness, brow raise,
inner/outer brow vertical movement, brow furrow, jaw opening, surprise, fear,
and disgust.

The same document also includes a `quori_controls` object containing the latest
mapped runtime values. When `--output` is provided, extraction automatically
writes both the detailed `*.features.json` report and a separate uploadable
`*.quori.json` file. `map_to_quori.py` remains available when you want to
regenerate the upload file after changing the mapping.

## Map features to Quori

```bash
pipeline/.venv/bin/python pipeline/map_to_quori.py \
  pipeline/outputs/gen_images/extremely_evil_grin.features.json \
  --output pipeline/outputs/gen_images/extremely_evil_grin.quori.json
```

The output contains render-control paths such as
`rig/quori_latest/propsrig/mouth/jawud/value` and their normalized values. These
paths are consumed directly by the fullscreen Quori demo. The mapping in
[quori_mapping.json](./quori_mapping.json) is intentionally marked
`provisional`; its coefficients are a starting point for calibration against
Quori's neutral and authored expression poses.

The mapping is expression-general: each Quori control is composed from reusable
features such as `smile`, `frown`, `jaw_open`, and brow movement rather than
being tied to a particular source image. Positive smile measurements drive
mouth widening, upward corner movement, vertical translation, and the main
Quori smile control, while frown measurements provide the opposing anger
components. The coefficients are still provisional and should be calibrated
against neutral, happy, sad, angry, surprised, and fearful reference images
before production use.

`calibration_profiles.json` defines the seven-expression reference set used for
validation: neutral, happy, sad, angry, surprised, fearful, and disgusted.
These profiles are feature targets, not hard-coded image outputs. New reference
images can be measured with the extractor and compared against the profiles
without changing the Quori control mapping.

## Process multiple generated faces

Run the complete batch pipeline with one command. It processes images
sequentially and produces one uploadable `.quori.json` per image:

```bash
PYTHONPATH=pipeline pipeline/.venv/bin/python pipeline/run_pipeline.py \
  pipeline/outputs/gen_images \
  --overlay
```

You can also pass individual images:

```bash
PYTHONPATH=pipeline pipeline/.venv/bin/python pipeline/run_pipeline.py \
  pipeline/outputs/gen_images/happy.png \
  pipeline/outputs/gen_images/sad.png \
  pipeline/outputs/gen_images/surprised.png
```

Each image produces a matching `.features.json` report and uploadable
`.quori.json` file. The command also writes `batch-summary.json` and continues
after an individual image failure, including images where MediaPipe cannot find
a face, so the rest of the batch is still tested.
Use `--fail-fast` to stop immediately on the first failure.
`quori_expression_calibration.json` records the brow
channels from Quori's authored emotion poses, so the landmark mapping can be
compared with the face's built-in neutral, happy, sad, concerned, surprise, and
anger shapes.
