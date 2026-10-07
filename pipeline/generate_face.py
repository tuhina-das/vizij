import torch
from diffusers import StableDiffusionXLPipeline
from pathlib import Path



expression = input("What expression should the face show? ") ##user input wowza
print("Requested expression:", expression)

##change/make the prompt better later but basically this is the prompt that will be used to generate the image
prompt = (
    f"Realistic close-up portait of an adult with a {expression} expression, "
    "natural facial anatomy, realistic eyes and lips, natural skin texture, "
    "facing directly toward the camera, head upright, "
    "entire face and eyebrows visible, soft even lighting, "
    "plain gray background"
)
##debugging shi,, take out later
print("Image prompt:", prompt)
print("GPU available:", torch.cuda.is_available())

##load the model here
pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    variant="fp16",
    use_safetensors=True,
)

pipe.enable_model_cpu_offload()
print("Model loaded!")

##gen an image woopwoop
result = pipe(
    prompt,
    width=1024,
    height=1024,
    num_inference_steps=30,
)

image = result.images[0]
##save it to the outputs/gen_images folder
output_dir = Path(__file__).resolve().parent / "outputs" / "gen_images"
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / "generated_face.png"
image.save(output_path)
print("Saved:", output_path)
print("Saved generated_face.png")