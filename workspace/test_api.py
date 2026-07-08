"""Test all available models."""
from openai import OpenAI
import os

c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
c.base_url = "https://njusehub.info/v1"

models = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "glm-5.2",
    "Qwen2.5-14B-Instruct",
]

for m in models:
    try:
        r = c.chat.completions.create(
            messages=[{"role": "user", "content": "say hi"}],
            model=m,
            max_tokens=10,
        )
        print(f"✅ {m}: {r.choices[0].message.content}")
    except Exception as e:
        print(f"❌ {m}: {type(e).__name__}")