"""Checks the real Storage setup: uploads, reads and deletes one test object.

Usage (from backend/, with the virtual environment active):
    python -m scripts.check_storage

It prints no credentials and leaves nothing behind in the bucket.
"""

import sys
import uuid

from app.services.photo_storage import StorageError, get_photo_storage

# The smallest valid PNG header: enough to prove bytes survive the round trip.
SAMPLE = b"\x89PNG\r\n\x1a\n" + b"storage-check"


def main() -> int:
    path = f"storage-check/{uuid.uuid4().hex}.png"
    uploaded = False
    try:
        storage = get_photo_storage()
        storage.upload(path, SAMPLE, "image/png")
        uploaded = True
        print("upload: OK")
        if storage.download(path) != SAMPLE:
            print("download: the content does not match")
            return 1
        print("download: OK")
        storage.delete(path)
        uploaded = False
        print("delete: OK")
    except StorageError as exc:
        print(f"FAILED: {exc}")
        if uploaded:
            print(f"Remove this object from the bucket by hand: {path}")
        return 1
    print("Storage is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
