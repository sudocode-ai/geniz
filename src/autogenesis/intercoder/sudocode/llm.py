import os
import litellm
from typing import Dict, List, Optional

from pydantic import BaseModel

from .round_info import get_round_info
from .keys import MODEL, API_BASE, API_KEY

N = 1


class ChatMessage(BaseModel):
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

    def to_string(self) -> str:
        return f"{self.role}: {self.content}"


def query_llm(prompt: str, *, system_message: str = '', previous_history: List[ChatMessage] = [], filename: Optional[str] = None, model=MODEL, n=N):
    messages: List[ChatMessage] = (
        previous_history + [ChatMessage(role='user', content=prompt)])
    if filename is not None:
        with open(f'{filename}.prompt.txt', 'w') as f:
            f.write(f'{model}\n\n{system_message}\n\n')
            for i, message in enumerate(messages):
                f.write(f'=== {i}: {message.role} ===\n')
                f.write(message.content)
                f.write('\n')

    final_messages = [msg.to_dict() for msg in messages]
    if system_message:
        final_messages = [
            {"role": "system", "content": system_message}] + final_messages
        
    round_info = get_round_info()
    session_id = round_info.session_id

    if n == 1:
        n = None
    response = litellm.completion(
        model=f"openai/{model}",
        api_key=API_KEY,
        api_base=API_BASE,
        messages=final_messages,
        temperature=1.2,
        num_retries=1,
        n=n,
        metadata={
            "generation_name": "autogenesis-0510",
            "generation_id": "autogenesis-0510",
            "version":  "0510",
            "trace_user_id": "ning",
            "session_id": session_id,
            "tags": ["autogenesis", MODEL],
        },
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
