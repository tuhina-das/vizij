import sys
from pathlib import Path

try:
    import torch
    from diffusers import AutoencoderKL, StableDiffusionXLPipeline
except ModuleNotFoundError as error:
    if error.name in {"torch", "diffusers"}:
        raise SystemExit(
            "The Stable Diffusion dependencies are installed in pipeline/.venv, "
            "not the system Python. From the repository root, run:\n\n"
            "  pipeline/.venv/bin/python pipeline/generate_face.py "
            '"your expression"\n'
        ) from error
    raise

# expression comes from the command line if given (python generate_face.py "sad"), otherwise ask
expression = " ".join(sys.argv[1:]) or input("What expression should the face show? ")
print("Requested expression:", expression)

##change/make the prompt better later but basically this is the prompt that will be used to generate the image
prompt = (
    f"Realistic close-up portrait of an adult with a {expression} expression, "
    "natural facial anatomy, realistic eyes and lips, natural skin texture, "
    "facing directly toward the camera, head upright, "
    "entire face and eyebrows visible, soft even lighting, "
    "plain gray background"
)
negative_prompt = "cartoon, profile view, side view, hands, cropped face, tilted head"
##debugging shi,, take out later
print("Image prompt:", prompt)

# pick the best available backend, same code runs on any machine
if torch.cuda.is_available():
    device, dtype = "cuda", torch.float16
elif torch.backends.mps.is_available():
    device, dtype = "mps", torch.float16
else:
    device, dtype = "cpu", torch.float32      # works, but very slow
print("Using device:", device)

##load the model here
# the fp16-fix VAE avoids the black/garbled images SDXL's stock VAE gives in fp16
kwargs = {}
if dtype == torch.float16:
    kwargs["vae"] = AutoencoderKL.from_pretrained(
        "madebyollin/sdxl-vae-fp16-fix", dtype=dtype)

pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    dtype=dtype,                # use torch_dtype= if your diffusers version is old
    variant="fp16",
    use_safetensors=True,
    **kwargs,
)

if device == "cuda":
    free_gb = torch.cuda.mem_get_info()[0] / 1e9
    if free_gb < 10:
        pipe.enable_model_cpu_offload()   # low-VRAM NVIDIA cards
    else:
        pipe.to("cuda")
else:
    pipe.to(device)
    pipe.enable_attention_slicing()       # lowers memory use on Mac / CPU
print("Model loaded!")

##gen an image woopwoop
result = pipe(
    prompt,
    negative_prompt=negative_prompt,
    width=1024,
    height=1024,
    num_inference_steps=30,
    generator=torch.Generator("cpu").manual_seed(0),   # change seed for a different face
)
image = result.images[0]

##save it to the outputs/gen_images folder
output_dir = Path(__file__).resolve().parent / "outputs" / "gen_images"
output_dir.mkdir(parents=True, exist_ok=True)

safe_name = "_".join(expression.lower().split())      # "very sad" -> "very_sad"
output_path = output_dir / f"{safe_name}.png"
image.save(output_path)
print("Saved:", output_path)