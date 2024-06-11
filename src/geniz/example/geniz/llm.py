import os
from typing import Dict, List, Optional

import litellm
from pydantic import BaseModel

BATCH_INFERENCE_N = 1


class ChatMessage(BaseModel):
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

    def to_string(self) -> str:
        return f"{self.role}: {self.content}"


def query_llm(prompt: str, *, system_message: str = '', previous_history: List[ChatMessage] = [], filename: Optional[str] = None):
    MODEL = os.getenv('MODEL', 'openai/Phi-3-mini-128k-instruct-a100')
    API_BASE = os.getenv('API_BASE', 'https://geniz.ai/v1')
    API_KEY = os.getenv('API_KEY', '')
    n = int(os.getenv('BATCH_INFERENCE_N', '1'))

    messages: List[ChatMessage] = (
        previous_history + [ChatMessage(role='user', content=prompt)])
    if filename is not None:
        with open(f'{filename}.prompt.txt', 'w') as f:
            f.write(f'{MODEL}\n\n{system_message}\n\n')
            for i, message in enumerate(messages):
                f.write(f'=== {i}: {message.role} ===\n')
                f.write(message.content)
                f.write('\n')

    final_messages = [msg.to_dict() for msg in messages]
    if system_message:
        final_messages = [
            {"role": "system", "content": system_message}] + final_messages


    if n == 1:
        n = None
    response = litellm.completion(
        model=MODEL,
        api_key=API_KEY,
        api_base=API_BASE,
        messages=final_messages,
        temperature=0.9,
        num_retries=1,
        n=n,
    )
    replys = [choice.message.content for choice in response.choices]
    histories = []
    for reply in replys:
        new_messages = messages + \
            [ChatMessage(role='assistant', content=reply)]
        histories.append(new_messages)
    if filename is not None:
        with open(f'{filename}.prompt.txt', 'a') as f:
            for i, reply in enumerate(replys):
                f.write(f'\n=== Reply {i} ===\n')
                f.write(reply)
    return replys, histories
