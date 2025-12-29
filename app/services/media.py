from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Final, Tuple
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

MEDIA_ROOT: Final[Path] = Path(_settings.media_root).resolve()
ANIMAL_PHOTOS_SUBDIR: Final[str] = _settings.animal_photos_subdir
AVATAR_SUBDIR: Final[str] = _settings.avatar_subdir


def _ensure_media_dirs_exist() -> None:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _ext_from_content_type(content_type: str) -> str:
    ct = (content_type or "").lower().strip()
    if ct in ("image/jpeg", "image/jpg"):
        return ".jpg"
    if ct == "image/png":
        return ".png"
    if ct == "image/webp":
        return ".webp"
    return ".bin"


async def _read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    buffer = BytesIO()
    total = 0
    try:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Max size is {max_bytes} bytes",
                )
            buffer.write(chunk)
    finally:
        await upload.close()
    return buffer.getvalue()


def _open_image_for_thumb(raw_bytes: bytes) -> Image.Image:
    """
    Открывает изображение только для генерации thumb.
    Основной файл не трогает и не перекодирует.
    """
    try:
        img = Image.open(BytesIO(raw_bytes))
        img = ImageOps.exif_transpose(img)
        img.load()
        return img
    except Exception as exc:  # noqa: BLE001
        logger.exception("Не удаётся открыть файл как изображение")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        ) from exc


def _make_thumb(img: Image.Image) -> Image.Image:
    """
    Делает миниатюру. Пропорции сохраняются.
    Если нужен квадрат — можно заменить на ImageOps.fit.
    """
    max_w = _settings.animal_thumb_max_width
    max_h = _settings.animal_thumb_max_height

    thumb = img.copy()

    # thumb обычно лучше без альфы — предсказуемый размер/вид
    if thumb.mode not in ("RGB",):
        # Если RGBA/LA/P — переводит в RGB с белым фоном
        background = Image.new("RGB", thumb.size, (255, 255, 255))
        if thumb.mode in ("RGBA", "LA") or (thumb.mode == "P" and "transparency" in thumb.info):
            background.paste(thumb.convert("RGBA"), mask=thumb.convert("RGBA").split()[-1])
            thumb = background
        else:
            thumb = thumb.convert("RGB")

    thumb.thumbnail((max_w, max_h), Image.LANCZOS)
    return thumb


def _encode_thumb(thumb: Image.Image, original_content_type: str) -> tuple[bytes, str]:
    """
    Thumb можно хранить JPEG почти всегда: меньше вес и лучше поддержка.
    Если тебе принципиально WEBP — можно включить.
    """
    quality = int(_settings.animal_thumb_quality)

    # Вариант A (рекомендую): thumb всегда JPEG — стабильный, компактный.
    buf = BytesIO()
    thumb.save(
        buf,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return buf.getvalue(), ".jpg"


async def save_animal_photo_file(
    owner_user_id: int,
    animal_id: int,
    upload: UploadFile,
) -> Tuple[str, str]:
    """
    Основник: сохраняется в точности как загружен (0 перекодирования, 0 сжатия).
    Thumb: генерируется отдельно и сжимается.
    """
    _ensure_media_dirs_exist()

    content_type = (upload.content_type or "").lower()
    if content_type not in _settings.animal_photo_allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type",
        )

    raw_bytes = await _read_upload_limited(upload, _settings.animal_photo_max_bytes)

    # Проверяет, что файл реально изображение (иначе можно подсунуть мусор с правильным MIME)
    img = _open_image_for_thumb(raw_bytes)

    base_dir = (
        MEDIA_ROOT
        / ANIMAL_PHOTOS_SUBDIR
        / str(owner_user_id)
        / str(animal_id)
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    base_name = uuid4().hex

    main_ext = _ext_from_content_type(content_type)
    main_filename = f"{base_name}{main_ext}"
    main_path = base_dir / main_filename

    # Основной файл: пишет как есть
    async with aiofiles.open(main_path, "wb") as f:
        await f.write(raw_bytes)

    # Thumb: генерирует и сохраняет отдельно
    thumb_img = _make_thumb(img)
    thumb_bytes, thumb_ext = _encode_thumb(thumb_img, content_type)

    thumb_filename = f"{base_name}_thumb{thumb_ext}"
    thumb_path = base_dir / thumb_filename

    async with aiofiles.open(thumb_path, "wb") as f:
        await f.write(thumb_bytes)

    logger.info(
        "Сохраняет фото животного (без перекодирования): user_id=%s animal_id=%s main=%s thumb=%s",
        owner_user_id,
        animal_id,
        main_path,
        thumb_path,
    )

    relative_main = f"{ANIMAL_PHOTOS_SUBDIR}/{owner_user_id}/{animal_id}/{main_filename}"
    relative_thumb = f"{ANIMAL_PHOTOS_SUBDIR}/{owner_user_id}/{animal_id}/{thumb_filename}"

    url = f"/media/{relative_main}"
    thumb_url = f"/media/{relative_thumb}"
    return url, thumb_url


def delete_media_file_by_url(url: str) -> None:
    if not url:
        return
    if not url.startswith("/media/"):
        logger.warning("Неожиданный формат media URL: %s", url)
        return

    relative = url[len("/media/") :]
    file_path = MEDIA_ROOT / relative

    try:
        os.remove(file_path)
        logger.info("Удаляет медиа-файл: %s", file_path)
    except FileNotFoundError:
        logger.info("Файл для удаления не найден: %s", file_path)
    except OSError as exc:
        logger.exception("Ошибка при удалении файла %s: %s", file_path, exc)
