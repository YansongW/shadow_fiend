import os

CACHE_ROOT = os.environ.get(
    "SHADOW_FIEND_CACHE_ROOT",
    os.path.expanduser("~/.cache/shadow_fiend-test"),
)
os.environ.setdefault("HF_HOME", os.path.join(CACHE_ROOT, "huggingface"))
os.environ.setdefault("MODELSCOPE_CACHE", os.path.join(CACHE_ROOT, "modelscope"))
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(CACHE_ROOT, "transformers"))
os.environ.setdefault("TORCH_HOME", os.path.join(CACHE_ROOT, "torch"))

from funasr import AutoModel
print("Downloading SenseVoice model...")
model = AutoModel(
    model="iic/SenseVoiceSmall",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    device="cpu",
)
print("SenseVoice model downloaded.")