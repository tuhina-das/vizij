"""Generate multiple Stable Diffusion expression images in one model session."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def load_pipeline():
    try:
        import torch
        from diffusers import AutoencoderKL, StableDiffusionXLPipeline
    except ModuleNotFoundError as error:
        if error.name in {"torch", "diffusers"}:
            raise SystemExit(
                "Stable Diffusion dependencies are installed in pipeline/.venv. "
                "Run this command with:\n\n"
                "  pipeline/.venv/bin/python pipeline/generate_faces.py "
                '"expression one" "expression two"\n'
            ) from error
        raise

    if torch.cuda.is_available():
        device, dtype = "cuda", torch.float16
    elif torch.backends.mps.is_available():
        device, dtype = "mps", torch.float16
    else:
        device, dtype = "cpu", torch.float32
    print(f"Using device: {device}")

    kwargs = {}
    if dtype == torch.float16:
        kwargs["vae"] = AutoencoderKL.from_pretrained(
            "madebyollin/sdxl-vae-fp16-fix", dtype=dtype
        )
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        dtype=dtype,
        variant="fp16",
        use_safetensors=True,
        **kwargs,
    )
    if device == "cuda":
        if torch.cuda.mem_get_info()[0] / 1e9 < 10:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")
    else:
        pipe.to(device)
        pipe.enable_attention_slicing()
    return pipe, torch


def safe_name(expression: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", expression.lower()).strip("_")
    return name or "expression"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "expressions",
        nargs="*",
        help="Expression prompts to generate, processed in order.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Text file with one expression prompt per line.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("outputs") / "gen_images",
    )
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    args = parser.parse_args()

    expressions = list(args.expressions)
    if args.file:
        expressions.extend(
            line.strip()
            for line in args.file.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    if not expressions:
        parser.error("Provide expressions or --file expressions.txt.")
    if args.steps < 1 or args.width < 1 or args.height < 1:
        parser.error("--steps, --width, and --height must be positive.")

    pipe, torch = load_pipeline()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    negative_prompt = "cartoon, profile view, side view, hands, cropped face, tilted head"
    for index, expression in enumerate(expressions):
        prompt = (
            f"Realistic close-up portrait of an adult with a {expression} expression, "
            "natural facial anatomy, realistic eyes and lips, natural skin texture, "
            "facing directly toward the camera, head upright, "
            "entire face and eyebrows visible, soft even lighting, plain gray background"
        )
        print(f"[{index + 1}/{len(expressions)}] Generating: {expression}", flush=True)
        result = pipe(
            prompt,
            negative_prompt=negative_prompt,
            width=args.width,
            height=args.height,
            num_inference_steps=args.steps,
            generator=torch.Generator("cpu").manual_seed(args.seed + index),
        )
        output_path = args.output_dir / f"{safe_name(expression)}.png"
        result.images[0].save(output_path)
        print(f"  Saved: {output_path}", flush=True)


if __name__ == "__main__":
    main()
