import re
import json
from openai import OpenAI
from src.ner.base import NERBase
from src.constants import NER_PROMPT


class NEROpenAI(NERBase):
    def __init__(self, api_key: str, base_url: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def predict(self, text: str) -> list[dict]:
        completion = self.client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[
                {"role": "system", "content": NER_PROMPT},
                {"role": "user", "content": text},
            ],
            # response_format=NERResponse,
        )
        result = completion.choices[0].message.content
        """
        ```json
[
  {
    "start": 2,
    "end": 5,
    "word": "TRANG",
    "entity_group": "PER",
  },
  {
    "start": 8,
    "end": 13,
    "word": "TÙY",
    "entity_group": "PER",
  },
  {
    "start": 29,
    "end": 38,
    "word": "TRANG TỬ",
    "entity_group": "PER",
  }
]
```
        """
        json_string = re.sub(r"^```json\n|\n```$", "", result.strip())
        entities = json.loads(json_string)
        return entities
