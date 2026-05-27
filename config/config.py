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


def _env_bool(key: str, default: str = "false") -> bool:
    v = _env(key, default) or default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


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
asr_streaming_model_name = _env("ASR_STREAMING_MODEL_NAME", "paraformer-zh-streaming")
asr_vad_model_name = _env("ASR_VAD_MODEL_NAME", "fsmn-vad")
asr_energy_threshold = float(_env("ASR_ENERGY_THRESHOLD", "0.006") or "0.006")
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

# MySQL 数据库配置
db_host = _env("DB_HOST", "localhost")
db_port = _env("DB_PORT", "3306")
db_user = _env("DB_USER", "root")
db_password = _env("DB_PASSWORD", "")
db_name = _env("DB_NAME", "meeting_ai")
db_charset = _env("DB_CHARSET", "utf8mb4")

# 构建数据库连接URL
database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset={db_charset}"

# JWT 认证配置
jwt_secret = _env("JWT_SECRET", "meeting-ai-jwt-secret-change-in-production")
jwt_expire_hours = int(_env("JWT_EXPIRE_HOURS", "72") or "72")

# 通义听悟实时转写（CreateTask + MeetingJoinUrl WebSocket）
tingwu_access_key_id = _env("ALIBABA_CLOUD_ACCESS_KEY_ID", "")
tingwu_access_key_secret = _env("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "")
tingwu_app_key = _env("TINGWU_APP_KEY", "")
tingwu_region = _env("TINGWU_REGION", "cn-beijing")
tingwu_domain = _env("TINGWU_DOMAIN", "tingwu.cn-beijing.aliyuncs.com")
tingwu_source_language = _env("TINGWU_SOURCE_LANGUAGE", "cn")
tingwu_audio_format = _env("TINGWU_AUDIO_FORMAT", "pcm")
tingwu_sample_rate = int(_env("TINGWU_SAMPLE_RATE", "16000") or "16000")
tingwu_transcription_output_level = int(
    _env("TINGWU_TRANSCRIPTION_OUTPUT_LEVEL", "2") or "2"
)
# 说话人分离（CreateTask Parameters.Transcription.DiarizationEnabled）
tingwu_diarization_enabled = _env_bool("TINGWU_DIARIZATION_ENABLED", "true")
_speaker_count_raw = _env("TINGWU_DIARIZATION_SPEAKER_COUNT", "0")
tingwu_diarization_speaker_count: int | None = (
    int(_speaker_count_raw) if _speaker_count_raw is not None and _speaker_count_raw != "" else None
)
