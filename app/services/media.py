from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Final, Tuple
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

MEDIA_ROOT: Final[Path] = Path(_settings.media_root).resolve()
ANIMAL_PHOTOS_SUBDIR: Final[str] = _settings.animal_photos_subdir
AVATAR_SUBDIR: Final[str] = _settings.avatar_subdir


def _ensure_media_dirs_exist() -> None:
    """
    Гарантирует существование базовой директории media.
    """
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _guess_extension_from_format(img_format: str) -> str:
    fmt = (img_format or "").upper()
    if fmt == "JPEG":
        return ".jpg"
    if fmt == "PNG":
        return ".png"
    if fmt == "WEBP":
        return ".webp"
    return ".jpg"


async def _read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """
    Читает файл из UploadFile с ограничением по размеру.
    При превышении max_bytes бросает HTTP 413.
    """
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


def _process_image_for_main(
    img: Image.Image,
) -> Image.Image:
    """
    Подготавливает основное изображение: уменьшаеет до допустимых размеров.
    """
    max_w = _settings.animal_photo_max_width
    max_h = _settings.animal_photo_max_height

    img = img.convert("RGB")
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def _process_image_for_thumb(
    img: Image.Image,
) -> Image.Image:
    """
    Подготавливает миниатюру: уменьшает до размеров превью.
    """
    max_w = _settings.animal_thumb_max_width
    max_h = _settings.animal_thumb_max_height

    thumb = img.copy()
    thumb.thumbnail((max_w, max_h), Image.LANCZOS)
    return thumb


async def save_animal_photo_file(
    owner_user_id: int,
    animal_id: int,
    upload: UploadFile,
) -> Tuple[str, str]:
    """
    Сохраняет фото животного с сжатием и генерацией миниатюры.
    Возвращает кортеж (url, thumb_url) для хранения в БД.

    Ограничивает:
    - MIME-тип;
    - максимальный размер файла;
    - максимальные размеры изображения.
    """
    _ensure_media_dirs_exist()

    content_type = (upload.content_type or "").lower()
    if content_type not in _settings.animal_photo_allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type",
        )

    raw_bytes = await _read_upload_limited(
        upload,
        _settings.animal_photo_max_bytes,
    )

    try:
        img = Image.open(BytesIO(raw_bytes))
    except Exception:
        logger.exception("Не удаётся открыть файл как изображение")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        )

    # Основное изображение
    main_img = _process_image_for_main(img)
    # Миниатюра
    thumb_img = _process_image_for_thumb(main_img)

    from uuid import uuid4

    base_dir = (
        MEDIA_ROOT
        / ANIMAL_PHOTOS_SUBDIR
        / str(owner_user_id)
        / str(animal_id)
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    # Определяет формат сохранения: JPEG или WEBP
    save_format = "JPEG"
    if content_type == "image/webp":
        save_format = "WEBP"

    ext = _guess_extension_from_format(save_format)
    base_name = uuid4().hex

    main_filename = f"{base_name}{ext}"
    thumb_filename = f"{base_name}_thumb{ext}"

    main_path = base_dir / main_filename
    thumb_path = base_dir / thumb_filename

    # Сохраняет основное изображение
    main_buffer = BytesIO()
    main_img.save(
        main_buffer,
        format=save_format,
        quality=_settings.animal_photo_quality,
        optimize=True,
    )
    main_bytes = main_buffer.getvalue()

    async with aiofiles.open(main_path, "wb") as f:
        await f.write(main_bytes)

    # Сохраняет миниатюру
    thumb_buffer = BytesIO()
    thumb_img.save(
        thumb_buffer,
        format=save_format,
        quality=_settings.animal_thumb_quality,
        optimize=True,
    )
    thumb_bytes = thumb_buffer.getvalue()

    async with aiofiles.open(thumb_path, "wb") as f:
        await f.write(thumb_bytes)

    logger.info(
        "Сохраняет фото животного: user_id=%s animal_id=%s main=%s thumb=%s",
        owner_user_id,
        animal_id,
        main_path,
        thumb_path,
    )

    relative_main = (
        f"{ANIMAL_PHOTOS_SUBDIR}/{owner_user_id}/{animal_id}/{main_filename}"
    )
    relative_thumb = (
        f"{ANIMAL_PHOTOS_SUBDIR}/{owner_user_id}/{animal_id}/{thumb_filename}"
    )

    url = f"/media/{relative_main}"
    thumb_url = f"/media/{relative_thumb}"

    return url, thumb_url


async def save_user_avatar_file(
    owner_user_id: int,
    file: UploadFile,
) -> str:
    """
    Сохраняет аватар пользователя, возвращает публичный URL.
    Старые файлы не трогает: их надо удалять отдельной функцией по URL.
    """
    content_type = file.content_type or ""
    if content_type not in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        logger.warning("Недопустимый тип файла для аватарки: %s", content_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG or WEBP images are allowed for avatar",
        )

    data = await file.read()
    max_bytes = _settings.animal_photo_max_bytes  # можно завести отдельный avatar_max_bytes
    if len(data) > max_bytes:
        logger.warning(
            "Размер файла аватарки превышает лимит: %s > %s байт",
            len(data),
            max_bytes,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar file is too large",
        )

    try:
        image = Image.open(BytesIO(data))
        image.verify()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Файл аватарки не является валидным изображением")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        ) from exc

    image = Image.open(BytesIO(data))
    image = image.convert("RGB")

    max_w = _settings.animal_photo_max_width
    max_h = _settings.animal_photo_max_height
    image.thumbnail((max_w, max_h))

    user_dir = MEDIA_ROOT / AVATAR_SUBDIR / str(owner_user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    ext = ".jpg"
    save_format = "JPEG"
    if content_type == "image/webp":
        ext = ".webp"
        save_format = "WEBP"
    elif content_type == "image/png":
        ext = ".png"
        save_format = "PNG"

    filename = f"{uuid4().hex}{ext}"
    file_path = user_dir / filename

    buffer = BytesIO()
    quality = _settings.animal_photo_quality
    image.save(buffer, format=save_format, quality=quality, optimize=True)
    buffer.seek(0)

    async with aiofiles.open(file_path, "wb") as out:
        await out.write(buffer.read())

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
    """
    Удаляет файл медиа по URL вида /media/....
    Тихо игнорирует отсутствие файла.
    """
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
