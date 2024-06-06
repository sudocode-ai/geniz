
import json
import string
import uuid
from math import log2
from pathlib import Path
from typing import Any, List

import yaml
from jinja2 import Template
from pydantic import BaseModel


class PersistStateToFile:

    @classmethod
    def filename(cls):
        return f'{cls.__name__}.json'

    @classmethod
    def load(cls):
        try:
            with open(cls.filename(), 'r') as f:
                json_dict = json.load(f)
                return cls(**json_dict)
        except:
            return cls()

    def save(self):
        with open(self.filename(), 'w') as f:
            f.write(self.model_dump_json(indent=2))


BASE62 = string.ascii_uppercase + string.ascii_lowercase + string.digits


def base62_encode(num) -> str:
    if num == 0:
        return BASE62[0]
    arr = []
    while num:
        num, rem = divmod(num, 62)
        arr.append(BASE62[rem])
    arr.reverse()
    return "".join(arr)


def alphanumeric_uuid() -> str:
    """Generate a base62-encoded UUID for IDs that need to be URL-safe."""
    uuid_hex = uuid.uuid4().hex
    uuid_int = int(uuid_hex, 16)
    return base62_encode(uuid_int)


def shorten_answer(var: Any, limit: int = 50) -> str:
    var_s = str(var)
    if len(var_s) > limit:
        var_s = var_s[:limit] + '...'
    return var_s


def shorten_list(var: List, limit: int = 5) -> str:
    if len(var) > limit:
        return str(var[:limit] + ['...'])
    return str(var)


def entropy_list(var: List) -> float:
    def normalize(data):
        """
        Normalize an array of integers to get probabilities.
        """
        data_sum = sum(data)
        probabilities = [val / data_sum for val in data]
        return probabilities

    def entropy(probabilities):
        """
        Calculate the entropy of a list of probabilities.
        """
        ent = 0.0
        for prob in probabilities:
            if prob > 0:
                ent += -prob * log2(prob)
        return ent

    return entropy(normalize(var))


def make_function_call_statement_str(input, output, function_name, limit=200) -> str:
    inputs = []
    for i in input:
        if isinstance(i, str):
            inputs.append(f'"{i}"')
        else:
            inputs.append(str(i))
    if not inputs:
        return ''
    args_str = ', '.join(inputs)

    if isinstance(output, str):
        output_str = f'"{output}"'
    elif isinstance(output, Exception):
        output_str = f'Exception("{str(output)}")'
    else:
        output_str = str(output)

    formatted_str = f'{function_name}({args_str}) -> {output_str}'
    if limit:
        return shorten_answer(formatted_str, limit=limit)
    return formatted_str


class PromptTemplate(BaseModel):
    """Lightweight prompt template implementation."""

    template: str
    input_variables: List[str]
    template_format: str  # ["f-string", "jinja2"]

    def format(self, **kwargs):
        """Format the prompt template."""
        if self.template_format == "jinja2":
            return self._format_jinja2(**kwargs)
        return self.template.format(**kwargs)

    def _format_jinja2(self, **kwargs):
        return Template(self.template).render(**kwargs)


def load_prompt(path: str) -> PromptTemplate:
    """Load prompt from file."""
    file_path = Path(path)
    if file_path.suffix == ".json":
        with open(file_path) as f:
            config = json.load(f)
    elif file_path.suffix == ".yaml":
        with open(file_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        raise ValueError(f"Got unsupported file type {file_path.suffix}")

    return PromptTemplate(
        template=config["template"],
        input_variables=config["input_variables"],
        template_format=(
            config["template_format"] if "template_format" in config else "f-string"
        ),
    )
