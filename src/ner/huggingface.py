import os
from typing import Callable
from huggingface_hub import InferenceClient
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

from src.ner.base import NERBase


class NERHugginFace(NERBase):
    def __init__(
        self,
        api_key: str = None,
        model_name: str = "NlpHUST/ner-vietnamese-electra-base",
        mode: str = "client",
    ):
        api_key = api_key or os.getenv("HF_TOKEN")
        if not api_key:
            raise ValueError("HF_TOKEN not found")
        self.model_name = model_name
        self.mode = mode
        if self.mode == "client":
            self.model = self._init_inference(api_key)
        else:
            self.model = self._init_model(model_name)

    def predict(self, text: str) -> list[dict]:
        """
        Result Sample:
        [
            TokenClassificationOutputElement(end=123, score=0.9991951, start=109, word='Nguyễn Văn Tảo', entity=None, entity_group='PERSON'),
            TokenClassificationOutputElement(end=161, score=0.9992889, start=138, word='Công an tỉnh Tiền Giang', entity=None, entity_group='ORGANIZATION'),
            TokenClassificationOutputElement(end=215, score=0.99907416, start=191, word='Công an huyện Châu Thành', entity=None, entity_group='ORGANIZATION')
        ]
        """
        if self.mode == "client":
            result = self.model.token_classification(
                text,
                model=self.model_name,
            )
        else:
            result = self.model(text)
        return result

    def _init_inference(self, api_key: str) -> InferenceClient:
        client = InferenceClient(
            provider="hf-inference",
            api_key=api_key,
        )
        return client

    def _init_model(self, model_name: str) -> Callable[[str], list[dict]]:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForTokenClassification.from_pretrained(model_name)
        model = pipeline("ner", model=_model, tokenizer=tokenizer)
        return model
