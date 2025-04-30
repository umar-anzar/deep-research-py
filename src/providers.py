import os
import re
import tiktoken
from pydantic import BaseModel
from openai import AsyncOpenAI
from typing import Optional, Type, TypeVar
from langchain_text_splitters import RecursiveCharacterTextSplitter


custom_model = os.getenv("MODEL", None)

openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_KEY", None),
    base_url=os.getenv("OPENAI_ENDPOINT", None)
)

def get_model():
    if custom_model:
        return custom_model
    raise ValueError("No model found")


MIN_CHUNK_SIZE = 140  # Same as MinChunkSize in JS


def num_tokens_from_string(string: str, model_name: str = "gpt-4o-mini"):
    """Helper to count tokens using OpenAI's tiktoken"""
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(string))


def trim_prompt(prompt: str, context_size: int = 128_000) -> str:
    if not prompt:
        return ''

    # Correct token counting
    length = num_tokens_from_string(prompt)

    if length <= context_size:
        return prompt

    overflow_tokens = length - context_size
    chunk_size = len(prompt) - overflow_tokens * 3  # 3 chars per token rough estimate

    if chunk_size < MIN_CHUNK_SIZE:
        return prompt[:MIN_CHUNK_SIZE]

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", ",", ">", "<", " ", ""],
        chunk_size=chunk_size, 
        chunk_overlap=0,
    )

    splits = splitter.split_text(prompt)
    trimmed_prompt = splits[0] if splits else ''

    if len(trimmed_prompt) == len(prompt):
        return trim_prompt(prompt[:chunk_size], context_size)

    return trim_prompt(trimmed_prompt, context_size)



T = TypeVar('T', bound=BaseModel)

def clean_json_string(raw: str) -> str:
    # Remove control characters that aren't allowed in JSON
    return re.sub(r'[\x00-\x1F]+', '', raw)

async def generate_object(model: str, schema: Type[T], system: str, prompt: str, abort_timeout: Optional[int] = None) -> T:
    response = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        response_format=schema,
        timeout=abort_timeout / 1000 if abort_timeout else None,
    )
    raw_data = response.choices[0].message.content
    try:
        clean_data = clean_json_string(raw_data)
        return schema.model_validate_json(clean_data)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from model: {e}\nRaw Output:\n{raw_data}")
    

async def generate_text(model: str, system: str, prompt: str, abort_timeout: Optional[int] = None) -> str:
    system_prompt = f"{system}\n\n Respond with the report in markdown only. Do not include any introductory or closing statements."
    response = await openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        timeout=abort_timeout / 1000 if abort_timeout else None,
    )
    return response.choices[0].message.content
    