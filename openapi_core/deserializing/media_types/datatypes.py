from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import Mapping

DeserializerCallable = Callable[[bytes], Any]
MediaTypeDeserializersDict = Dict[str, DeserializerCallable]


@dataclass(frozen=True)
class MultipartPart:
    """A single part of a positional (unnamed) multipart media type.

    ``content_type`` is the bare media type taken from the part's own
    Content-Type header, ``parameters`` holds its parameters (e.g. the
    nested boundary) and ``payload`` keeps the raw, transfer-decoded bytes.
    """

    content_type: str
    parameters: Mapping[str, str]
    payload: bytes
