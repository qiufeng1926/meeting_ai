import os
import asyncio
from zhipuai import ZhipuAI
from concurrent.futures import ThreadPoolExecutor
from utils.logger import get_logger

logger = get_logger("glm_client")

from config.config import glm_api_key, glm_model, glm_temperature
from llm.prompt import (
    SYSTEM_PROMPT,
    build_meeting_prompt
)


class GLMClient:

    def __init__(
        self,
        api_key=glm_api_key,
        model=glm_model
    ):

        self.api_key = api_key or os.getenv("GLM_API_KEY")

        if not self.api_key:
            raise Exception("未找到 GLM_API_KEY")

        self.client = ZhipuAI(
            api_key=self.api_key
        )

        self.model = model
        
        # 创建线程池用于异步执行
        self.executor = ThreadPoolExecutor(max_workers=4)

    def chat(
        self,
        prompt: str,
        temperature: float = glm_temperature
    ):

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
        )

        return response.choices[0].message.content
    
    async def chat_async(
        self,
        prompt: str,
        temperature: float = glm_temperature
    ):
        """
        异步聊天
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.chat, 
            prompt, 
            temperature
        )

    def summary_meeting(
        self,
        transcript: str
    ):

        prompt = build_meeting_prompt(
            transcript
        )

        return self.chat(prompt)
    
    async def summary_meeting_async(
        self,
        transcript: str
    ):
        """
        异步生成会议纪要
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.summary_meeting, transcript)


if __name__ == "__main__":
    logger_main = get_logger("glm_test")
    client = GLMClient()

    text = """
    今天召开项目会议。
    
    张三负责前端。
    李四负责后端。
    
    预计下周上线。
    """

    result = client.summary_meeting(text)

    logger_main.info(result)
