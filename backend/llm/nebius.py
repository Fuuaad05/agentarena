import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class NebiusLLM:
    def __init__(self):
        api_key = os.getenv("NEBIUS_API_KEY")
        base_url = os.getenv("NEBIUS_BASE_URL")

        self.model = os.getenv(
            "NEBIUS_MODEL",
            "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        )

        if not api_key:
            raise RuntimeError("NEBIUS_API_KEY is missing.")

        if not base_url:
            raise RuntimeError("NEBIUS_BASE_URL is missing.")

        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=45.0,
            max_retries=0,
        )

    def chat(
        self,
        messages,
        tools=None,
        max_tokens=1500,
        timeout=None,
    ):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
        }

        if timeout is not None:
            kwargs["timeout"] = timeout

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        if response.usage:
            for key in self.usage:
                self.usage[key] += getattr(response.usage, key, 0) or 0
        return response