from domain.base import BaseEntity, BaseValueObject


class SampleEntity(BaseEntity):
    def __init__(self, item_id: str):
        self._id = item_id

    def get_id(self) -> str:
        return self._id


class SampleVO(BaseValueObject):
    def __init__(self, value: int):
        self.value = value

    def validate(self) -> None:
        if self.value < 0:
            raise ValueError("Value must be non-negative")


def test_base_abstractions():
    entity = SampleEntity("abc-123")
    assert entity.get_id() == "abc-123"

    vo = SampleVO(42)
    vo.validate()
    assert vo.value == 42
