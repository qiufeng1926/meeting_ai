from dotenv import load_dotenv
import os
from pathlib import Path


load_dotenv()

_project_root = Path(__file__).resolve().parent.parent


def _env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    if v is None or v == "":
        return default
    return v


def _path_from_env(key: str, default_relative: str) -> str:
    raw = _env(key)
    if raw is None:
        return str(_project_root / default_relative)
    p = Path(raw)
    if not p.is_absolute():
        return str(_project_root / p)
    return str(p)


# ASR 配置
asr_model_name = _env("ASR_MODEL_NAME", "paraformer-zh")
asr_device = _env("ASR_DEVICE", "cpu")
ffmpeg_path = _env("FFMPEG_PATH", r"D:\AI\ffmpeg-8.1.1-essentials_build\bin")

# LLM 配置
glm_api_key = _env("GLM_API_KEY", "")
glm_model = _env("GLM_MODEL", "glm-4-flash")
glm_temperature = float(_env("GLM_TEMPERATURE", "0.3") or "0.3")

# 文件路径配置
upload_dir = _path_from_env("UPLOAD_DIR", "upload")
output_dir = _path_from_env("OUTPUT_DIR", "output")

# ASR 示例文件路径
asr_example_audio = _path_from_env("ASR_EXAMPLE_AUDIO", "asr/example/asr_example.wav")
asr_hotword_file = _path_from_env("ASR_HOTWORD_FILE", "asr/example/hotword.txt")
