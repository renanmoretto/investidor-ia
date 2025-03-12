import os
import time
import json

from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv(override=True)


gemini_api_key = os.getenv('GEMINI_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')


def _ask_gemini(
    model: str,
    temperature: float,
    prompt: str,
    pdf_content: bytes | None = None,
):
    client = genai.Client(api_key=gemini_api_key)
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
    model: str = 'gemini-1.5-flash-8b',
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


# def get_model():
#     if gemini_api_key:
#         return GeminiModel('gemini-2.0-flash', provider='google-gla')
#     elif openai_api_key:
#         return OpenAIModel('gpt-4o-mini', provider='openai')
#     else:
#         raise ValueError('No API key found')


# model = get_model()
