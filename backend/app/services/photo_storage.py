"""Profile photos in a private Supabase Storage bucket (HU-2.7).

Only this server holds the service key. Browsers never talk to Storage: they
ask the API, which checks the session first and then streams the bytes.
"""

from typing import Protocol

import httpx

from app.core.config import get_settings

MAX_PHOTO_BYTES = 2 * 1024 * 1024

# Formats are recognized by their first bytes, not by the name or the type the
# client declares: both can be faked. SVG is deliberately absent because it can
# carry scripts.
_JPEG = ("jpg", "image/jpeg")
_PNG = ("png", "image/png")
_WEBP = ("webp", "image/webp")
_TYPE_BY_EXTENSION = {"jpg": _JPEG[1], "png": _PNG[1], "webp": _WEBP[1]}


def detect_image(content: bytes) -> tuple[str, str] | None:
    """(extension, content type) of a supported image, or None."""
    if content.startswith(b"\xff\xd8\xff"):
        return _JPEG
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return _PNG
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return _WEBP
    return None


def content_type_of(path: str) -> str:
    """Content type of a stored photo, from the extension the server itself chose."""
    return _TYPE_BY_EXTENSION[path.rsplit(".", 1)[-1]]


class StorageError(Exception):
    """Storage failed or is not configured. Details stay in the server log."""


class PhotoStorage(Protocol):
    def upload(self, path: str, content: bytes, content_type: str) -> None: ...

    def download(self, path: str) -> bytes: ...

    def delete(self, path: str) -> None: ...


class SupabasePhotoStorage:
    def __init__(self, url: str, service_key: str, bucket: str) -> None:
        self._base = f"{url.rstrip('/')}/storage/v1/object/{bucket}"
        self._headers = {"Authorization": f"Bearer {service_key}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            response = httpx.request(
                method,
                f"{self._base}/{path}",
                content=content,
                headers={**self._headers, **(headers or {})},
                timeout=15,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # From here on, only the type and status: never the URL or headers.
            status = getattr(getattr(exc, "response", None), "status_code", "no response")
            raise StorageError(
                f"Storage {method} failed: {type(exc).__name__} ({status})"
            ) from None
        return response

    def upload(self, path: str, content: bytes, content_type: str) -> None:
        self._request("POST", path, content=content, headers={"Content-Type": content_type})

    def download(self, path: str) -> bytes:
        return self._request("GET", path).content

    def delete(self, path: str) -> None:
        self._request("DELETE", path)


def get_photo_storage() -> PhotoStorage:
    """The configured client, or StorageError if Storage is not set up."""
    settings = get_settings()
    if (
        not settings.supabase_url
        or settings.supabase_service_role_key is None
        or not settings.supabase_storage_bucket
    ):
        raise StorageError("Storage is not configured")
    return SupabasePhotoStorage(
        settings.supabase_url,
        settings.supabase_service_role_key.get_secret_value(),
        settings.supabase_storage_bucket,
    )
