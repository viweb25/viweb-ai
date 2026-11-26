from fastapi import Request

from vi_api.interfaces.http.errors import ApiError, ErrorCode

MAX_IMAGE_BYTES = 5 * 1024 * 1024


async def read_limited(request: Request, limit: int, message: str) -> bytes:
    """Read the request body, stopping as soon as it exceeds ``limit`` bytes."""
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise ApiError(413, ErrorCode.IMAGE_TOO_LARGE, message)
        body.extend(chunk)
    return bytes(body)


async def read_jpeg_frame(request: Request, message: str = "A JPEG frame is required") -> bytes:
    if request.headers.get("content-type") != "image/jpeg":
        raise ApiError(415, ErrorCode.UNSUPPORTED_IMAGE_TYPE, message)
    return await read_limited(request, MAX_IMAGE_BYTES, "Image exceeds 5 MiB")


async def read_jpeg(request: Request) -> bytes:
    image = await read_jpeg_frame(request, "Send a JPEG image")
    if not image.startswith(b"\xff\xd8\xff") or not image.endswith(b"\xff\xd9"):
        raise ApiError(422, ErrorCode.INVALID_IMAGE, "Invalid JPEG framing")
    return image
