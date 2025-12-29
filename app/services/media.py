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


def _read_image_bytes_limited(data: bytes, max_bytes: int) -> None:
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {max_bytes} bytes",
        )


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


def _open_image_safely(raw_bytes: bytes) -> Image.Image:
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


def _resize_keep_aspect(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    out = img.copy()
    out.thumbnail((max_w, max_h), Image.LANCZOS)
    return out


def _make_thumb(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    thumb = img.copy()
    thumb.thumbnail((max_w, max_h), Image.LANCZOS)
    return thumb


def _guess_extension_from_content_type(content_type: str) -> str:
    ct = (content_type or "").lower()
    if ct in ("image/jpeg", "image/jpg"):
        return ".jpg"
    if ct == "image/png":
        return ".png"
    if ct == "image/webp":
        return ".webp"
    return ".jpg"


def _encode_thumb_image(
    img: Image.Image,
    content_type: str,
) -> tuple[bytes, str]:
    """
    Возвращает (bytes, ext) для миниатюры.

    Thumb остаётся миниатюрой: отдельный ресайз и умеренное качество.
    """
    max_w = _settings.animal_thumb_max_width
    max_h = _settings.animal_thumb_max_height

    thumb = _make_thumb(img, max_w, max_h)
    rgb = thumb.convert("RGB")

    if content_type == "image/webp":
        buf = BytesIO()
        rgb.save(
            buf,
            format="WEBP",
            quality=int(_settings.animal_thumb_quality),
            method=6,
        )
        return buf.getvalue(), ".webp"

    buf = BytesIO()
    rgb.save(
        buf,
        format="JPEG",
        quality=int(_settings.animal_thumb_quality),
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
    Сохраняет фото животного и миниатюру.
    Возвращает (url, thumb_url).

    ВАЖНО: основной файл сохраняется БЕЗ перекодирования/сжатия (raw bytes as-is).
    Thumb генерируется отдельно как миниатюра.
    """
    _ensure_media_dirs_exist()

    content_type = (upload.content_type or "").lower()
    if content_type not in _settings.animal_photo_allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type",
        )

    raw_bytes = await _read_upload_limited(upload, _settings.animal_photo_max_bytes)

    # Проверяет, что это изображение (и одновременно нормализует ориентацию для thumb)
    img = _open_image_safely(raw_bytes)

    base_dir = (
        MEDIA_ROOT
        / ANIMAL_PHOTOS_SUBDIR
        / str(owner_user_id)
        / str(animal_id)
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    base_name = uuid4().hex

    # Основной файл: сохраняется как есть
    main_ext = _guess_extension_from_content_type(content_type)
    main_filename = f"{base_name}{main_ext}"
    main_path = base_dir / main_filename

    async with aiofiles.open(main_path, "wb") as f:
        await f.write(raw_bytes)

    # Миниатюра: отдельный файл
    thumb_bytes, thumb_ext = _encode_thumb_image(img, content_type)
    thumb_filename = f"{base_name}_thumb{thumb_ext}"
    thumb_path = base_dir / thumb_filename

    async with aiofiles.open(thumb_path, "wb") as f:
        await f.write(thumb_bytes)

    logger.info(
        "Сохраняет фото животного: user_id=%s animal_id=%s main=%s thumb=%s",
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


async def save_user_avatar_file(
    owner_user_id: int,
    file: UploadFile,
) -> str:
    """
    Сохраняет аватар пользователя, возвращает публичный URL.

    Оставлено как было: аватар обычно допустимо ресайзить и перекодировать.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        logger.warning("Недопустимый тип файла для аватарки: %s", content_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG or WEBP images are allowed for avatar",
        )

    data = await file.read()
    _read_image_bytes_limited(data, _settings.animal_photo_max_bytes)

    img = _open_image_safely(data)

    max_w = _settings.animal_photo_max_width
    max_h = _settings.animal_photo_max_height
    img = _resize_keep_aspect(img, max_w, max_h)

    user_dir = MEDIA_ROOT / AVATAR_SUBDIR / str(owner_user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    base_name = uuid4().hex

    # Минимально сохраняет совместимость: если PNG — PNG, если WEBP — WEBP, иначе JPEG
    if content_type == "image/png":
        filename = f"{base_name}.png"
        save_format = "PNG"
        out_img = img.convert("RGBA") if img.mode != "RGBA" else img
        buf = BytesIO()
        out_img.save(buf, format=save_format, optimize=True, compress_level=9)
        out_bytes = buf.getvalue()
    elif content_type == "image/webp":
        filename = f"{base_name}.webp"
        save_format = "WEBP"
        out_img = img.convert("RGB")
        buf = BytesIO()
        out_img.save(
            buf,
            format=save_format,
            quality=int(_settings.animal_photo_quality),
            method=6,
        )
        out_bytes = buf.getvalue()
    else:
        filename = f"{base_name}.jpg"
        save_format = "JPEG"
        out_img = img.convert("RGB")
        buf = BytesIO()
        out_img.save(
            buf,
            format=save_format,
            quality=int(_settings.animal_photo_quality),
            optimize=True,
            progressive=True,
        )
        out_bytes = buf.getvalue()

    file_path = user_dir / filename
    async with aiofiles.open(file_path, "wb") as out:
        await out.write(out_bytes)

    relative_path = file_path.relative_to(MEDIA_ROOT)
    url = f"/media/{relative_path.as_posix()}"

    logger.info(
        "Сохраняет аватар пользователя %s в файл %s (url=%s)",
        owner_user_id,
        file_path,
        url,
    )

    return url


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
