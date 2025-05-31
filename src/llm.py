import os
import time
import json

from google import genai
from pydantic import BaseModel


from src.settings import PROVIDER, API_KEY


def _ask_gemini(
    model: str,
    temperature: float,
    prompt: str,
    pdf_content: bytes | None = None,
):
    if not API_KEY:
        raise ValueError('Por favor, configure a API key no menu de configurações')

    client = genai.Client(api_key=API_KEY)
    if pdf_content:
        content = genai.types.Part.from_bytes(
            data=pdf_content,
            mime_type='application/pdf',
        )
        contents = [content, prompt]
    else:
        contents = [prompt]

    model_response = client.models.generate_content(
        model=model,
        contents=contents,
        config=genai.types.GenerateContentConfig(
            temperature=temperature,
        ),
    )

    return model_response


def ask(
    message: str,
    model: str = 'gemini-2.0-flash',
    temperature: float = 0.8,
    pdf_content: bytes | None = None,
    model_output: BaseModel | None = None,
    retries: int = 3,  # number of retries if model parsing fails
) -> str:
    for attempt in range(retries):
        try:
            model_response = _ask_gemini(
                model=model,
                temperature=temperature,
                prompt=message,
                pdf_content=pdf_content,
            )

            if model_output:
                _json_text = model_response.text.replace('json\n', '').replace('```json', '').replace('```', '')
                response_json = json.loads(_json_text)
                return model_output(**response_json)
            else:
                return model_response.text
        except Exception as e:
            if attempt == retries - 1:  # Last attempt
                raise Exception(f'Failed after {retries} attempts. Last error: {str(e)}')
            print(f'Failed attempt {attempt + 1} of {retries}: {str(e)}')
            time.sleep(1)
            continue
