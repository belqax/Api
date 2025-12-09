from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Animal, AnimalPhoto


async def list_photos_for_animal(
    db: AsyncSession,
    *,
    animal_id: int,
) -> List[AnimalPhoto]:
    stmt = (
        select(AnimalPhoto)
        .where(AnimalPhoto.animal_id == animal_id)
        .order_by(AnimalPhoto.position.asc(), AnimalPhoto.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_animal_photo(
    db: AsyncSession,
    *,
    animal: Animal,
    url: str,
    thumb_url: str,
) -> AnimalPhoto:
    """
    Создаёт запись AnimalPhoto.
    Первое фото для животного делает основным.
    """
    stmt_count = select(func.count(AnimalPhoto.id)).where(
        AnimalPhoto.animal_id == animal.id
    )
    result_count = await db.execute(stmt_count)
    count = int(result_count.scalar_one() or 0)

    is_primary = count == 0
    position = count

    photo = AnimalPhoto(
        animal_id=animal.id,
        url=url,
        thumb_url=thumb_url,
        is_primary=is_primary,
        position=position,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


async def get_photo_by_id(
    db: AsyncSession,
    *,
    photo_id: int,
) -> Optional[AnimalPhoto]:
    stmt = select(AnimalPhoto).where(AnimalPhoto.id == photo_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def set_primary_photo(
    db: AsyncSession,
    *,
    animal_id: int,
    photo_id: int,
) -> None:
    photos = await list_photos_for_animal(db, animal_id=animal_id)
    target = None
    for p in photos:
        if p.id == photo_id:
            target = p
            break

    if target is None:
        raise ValueError("Photo does not belong to this animal or not found")

    for p in photos:
        p.is_primary = p.id == photo_id

    await db.commit()


async def reorder_photos(
    db: AsyncSession,
    *,
    animal_id: int,
    ordered_ids: List[int],
) -> None:
    photos = await list_photos_for_animal(db, animal_id=animal_id)
    photos_map = {p.id: p for p in photos}

    if set(ordered_ids) != set(photos_map.keys()):
        raise ValueError("photo_ids must match exactly the set of animal photos")

    for idx, pid in enumerate(ordered_ids):
        photos_map[pid].position = idx

    await db.commit()


async def delete_photo(
    db: AsyncSession,
    *,
    photo: AnimalPhoto,
) -> None:
    animal_id = photo.animal_id
    was_primary = photo.is_primary

    await db.delete(photo)
    await db.commit()

    if was_primary:
        photos = await list_photos_for_animal(db, animal_id=animal_id)
        if photos and not any(p.is_primary for p in photos):
            first = min(photos, key=lambda p: p.position)
            first.is_primary = True
            await db.commit()
