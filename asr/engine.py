import os
from pathlib import Path
from funasr import AutoModel
import numpy as np
import io


class FunASREngine:
    def __init__(
        self,
        model_name: str = "paraformer-zh",
        device: str = "cpu",
        ffmpeg_path: str = r"D:\AI\ffmpeg-8.1.1-essentials_build\bin",
    ):
        """
        FunASR 语音识别引擎
        """

        # 配置 ffmpeg
        os.environ["PATH"] += os.pathsep + ffmpeg_path

        # 初始化模型
        self.model = AutoModel(
            model=model_name,
            device=device,
            disable_update=True,
        )

    def transcribe(self, audio_path: str) -> str:
        """
        音频转文字（批量模式）
        """

        audio_path = str(Path(audio_path).resolve())
        print(f"[INFO] 音频文件：{audio_path}")

        result = self.model.generate(
            input=audio_path,
            batch_size_s=300,
        )

        text = result[0]["text"]

        # 去除空格
        text = text.replace(" ", "")

        return text

    def transcribe_stream(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """
        流式音频转文字
        :param audio_data: 音频数据（PCM 格式）
        :param sample_rate: 采样率
        :return: 识别文本
        """
        try:
            # 将字节数据转换为 numpy 数组
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # 归一化到 [-1, 1]
            audio_float = audio_np.astype(np.float32) / 32768.0
            
            # 使用模型进行识别
            result = self.model.generate(
                input=audio_float,
                batch_size_s=300,
                fs=sample_rate,
            )
            
            if result and len(result) > 0:
                text = result[0].get("text", "")
                return text.replace(" ", "")
            return ""
        except Exception as e:
            print(f"[ERROR] 流式识别失败: {e}")
            return ""


if __name__ == "__main__":

    engine = FunASREngine()

    text = engine.transcribe(
        r"./example/asr_example.wav"
    )

    print("\n========== ASR RESULT ==========\n")
    print(text)
