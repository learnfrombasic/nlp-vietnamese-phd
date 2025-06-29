from abc import abstractmethod, ABC


class NERBase(ABC):
    @abstractmethod
    def predict(self, text: str) -> list[dict]:
        pass
