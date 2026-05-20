import os
from zhipuai import ZhipuAI

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

    def summary_meeting(
        self,
        transcript: str
    ):

        prompt = build_meeting_prompt(
            transcript
        )

        return self.chat(prompt)


if __name__ == "__main__":

    client = GLMClient()

    text = """
    今天召开项目会议。
    
    张三负责前端。
    李四负责后端。
    
    预计下周上线。
    """

    result = client.summary_meeting(text)

    print(result)
