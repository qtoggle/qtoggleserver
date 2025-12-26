import pytest

from qtoggleserver.utils.template import render, render_async, render_native


class Dummy:
    def __init__(self, value: int) -> None:
        self.value = value

    def __eq__(self, other) -> bool:
        return self.value == other.value


@pytest.mark.parametrize(
    "source, context, result",
    [
        ("some dummy text", {}, "some dummy text"),
        ("{{num}}", {"num": 13}, "13"),
        ("number {{num}}", {"num": 13}, "number 13"),
        ("{% if cond %}first{% else %}second{% endif %}", {"cond": True}, "first"),
        ("{% if cond %}first{% else %}second{% endif %}", {"cond": False}, "second"),
    ],
)
def test_render(source, context, result):
    assert render(source, context) == result


@pytest.mark.parametrize(
    "source, context, result",
    [
        ("some dummy text", {}, "some dummy text"),
        ("{{num}}", {"num": 13}, "13"),
        ("number {{num}}", {"num": 13}, "number 13"),
        ("{% if cond %}first{% else %}second{% endif %}", {"cond": True}, "first"),
        ("{% if cond %}first{% else %}second{% endif %}", {"cond": False}, "second"),
    ],
)
async def test_render_async(source, context, result):
    assert await render_async(source, context) == result


@pytest.mark.parametrize(
    "source, context, result",
    [
        ("some dummy text", {}, "some dummy text"),
        ("{{num}}", {"num": 13}, 13),
        ("number {{num}}", {"num": 13}, "number 13"),
        ("{% if cond %}first{% else %}second{% endif %}", {"cond": True}, "first"),
        ("{% if cond %}first{% else %}second{% endif %}", {"cond": False}, "second"),
        ("{{value}}", {"value": {"dict": "with", "stuff": ["a", "b"]}}, {"dict": "with", "stuff": ["a", "b"]}),
        ("{{value}}", {"value": Dummy(13)}, Dummy(13)),
    ],
)
async def test_render_native(source, context, result):
    assert await render_native(source, context) == result
