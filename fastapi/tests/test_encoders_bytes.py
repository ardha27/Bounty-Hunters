import base64
from fastapi.encoders import jsonable_encoder


def test_bytes_encoded_as_base64():
    result = jsonable_encoder({"data": b"hello world"})
    assert result["data"] == base64.b64encode(b"hello world").decode("ascii")


def test_bytes_encoded_as_hex():
    result = jsonable_encoder(
        {"data": b"hello world"}, bytes_encoding="hex"
    )
    assert result["data"] == b"hello world".hex()


def test_memoryview_encoded_as_base64():
    data = memoryview(b"test data")
    result = jsonable_encoder({"data": data})
    assert result["data"] == base64.b64encode(b"test data").decode("ascii")


def test_memoryview_encoded_as_hex():
    data = memoryview(b"test data")
    result = jsonable_encoder({"data": data}, bytes_encoding="hex")
    assert result["data"] == b"test data".hex()


def test_bytes_in_list():
    result = jsonable_encoder([b"one", b"two"])
    assert result == [
        base64.b64encode(b"one").decode("ascii"),
        base64.b64encode(b"two").decode("ascii"),
    ]


def test_other_types_unchanged():
    result = jsonable_encoder({"num": 42, "text": "hello", "none": None})
    assert result == {"num": 42, "text": "hello", "none": None}
