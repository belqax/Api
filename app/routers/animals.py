from __future__ import annotations

from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..deps import get_db, get_current_user
from ..models import User, Animal
from ..schemas import (
    AnimalWithPhotos,
    AnimalCreateRequest,
    AnimalUpdateRequest,
    AnimalPhotosReorderRequest,
)
from ..repositories.animal_repository import (
    create_animal,
    get_animal_by_id,
    list_animals_for_owner,
    update_animal,
    delete_animal,
)
from ..repositories.animal_photo_repository import (
    create_animal_photo,
    get_photo_by_id,
    set_primary_photo,
    reorder_photos,
    delete_photo,
)
from ..services.media import save_animal_photo_file, delete_media_file_by_url

router = APIRouter(prefix="/animals", tags=["animals"])


async def _get_owned_animal_or_404(
    db: AsyncSession,
    *,
    animal_id: int,
    current_user: User,
) -> Animal:
    animal = await get_animal_by_id(db, animal_id=animal_id)
    if animal is None or animal.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found",
        )
    return animal


@router.get("", response_model=List[AnimalWithPhotos])
async def list_my_animals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AnimalWithPhotos]:
    animals = await list_animals_for_owner(db, owner_user_id=current_user.id)
    return [AnimalWithPhotos.model_validate(a) for a in animals]


@router.post("", response_model=AnimalWithPhotos)
async def create_my_animal(
    payload: AnimalCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. создаём животное корректно
    animal = await create_animal(
        db=db,
        owner_user_id=current_user.id,
        payload=payload,
    )

    # 2. повторно загружаем с eager-load, чтобы Pydantic не триггерил lazy load
    stmt = (
        select(Animal)
        .options(selectinload(Animal.photos))
        .where(Animal.id == animal.id)
    )
    animal = (await db.execute(stmt)).scalar_one()

    return AnimalWithPhotos.model_validate(animal)


@router.get("/{animal_id}", response_model=AnimalWithPhotos)
async def get_animal(
    animal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await _get_owned_animal_or_404(
        db,
        animal_id=animal_id,
        current_user=current_user,
    )
    return AnimalWithPhotos.model_validate(animal)


@router.put("/{animal_id}", response_model=AnimalWithPhotos)
async def update_my_animal(
    animal_id: int,
    payload: AnimalUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await _get_owned_animal_or_404(
        db,
        animal_id=animal_id,
        current_user=current_user,
    )
    animal = await update_animal(db, animal=animal, payload=payload)
    return AnimalWithPhotos.model_validate(animal)


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_animal(
    animal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    animal = await _get_owned_animal_or_404(
        db,
        animal_id=animal_id,
        current_user=current_user,
    )
    await delete_animal(db, animal=animal)


# ---------- ФОТО ЖИВОТНЫХ ----------

@router.post(
    "/{animal_id}/photos",
    response_model=AnimalWithPhotos,
    status_code=status.HTTP_201_CREATED,
)
async def upload_animal_photo(
    animal_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    """
    Загружает фото животного, сжимает, создаёт миниатюру
    и возвращает обновлённую карточку животного.
    """
    animal = await _get_owned_animal_or_404(
        db,
        animal_id=animal_id,
        current_user=current_user,
    )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content-Type header is required for image upload",
        )

    url, thumb_url = await save_animal_photo_file(
        owner_user_id=current_user.id,
        animal_id=animal.id,
        upload=file,
    )

    await create_animal_photo(
        db,
        animal=animal,
        url=url,
        thumb_url=thumb_url,
    )
    await db.refresh(animal)

    return AnimalWithPhotos.model_validate(animal)


@router.put(
    "/{animal_id}/photos/reorder",
    response_model=AnimalWithPhotos,
)
async def reorder_animal_photos(
    animal_id: int,
    payload: AnimalPhotosReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await _get_owned_animal_or_404(
        db,
        animal_id=animal_id,
        current_user=current_user,
    )

    try:
        await reorder_photos(
            db,
            animal_id=animal.id,
            ordered_ids=payload.photo_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    await db.refresh(animal)
    return AnimalWithPhotos.model_validate(animal)


@router.put(
    "/{animal_id}/photos/{photo_id}/primary",
    response_model=AnimalWithPhotos,
)
async def set_animal_primary_photo(
    animal_id: int,
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await _get_owned_animal_or_404(
        db,
        animal_id=animal_id,
        current_user=current_user,
    )

    photo = await get_photo_by_id(db, photo_id=photo_id)
    if photo is None or photo.animal_id != animal.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    await set_primary_photo(
        db,
        animal_id=animal.id,
        photo_id=photo.id,
    )

    await db.refresh(animal)
    return AnimalWithPhotos.model_validate(animal)


@router.delete(
    "/{animal_id}/photos/{photo_id}",
    response_model=AnimalWithPhotos,
)
async def delete_animal_photo_endpoint(
    animal_id: int,
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await _get_owned_animal_or_404(
        db,
        animal_id=animal_id,
        current_user=current_user,
    )

    photo = await get_photo_by_id(db, photo_id=photo_id)
    if photo is None or photo.animal_id != animal.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    url_to_delete = photo.url
    thumb_to_delete = photo.thumb_url or None

    await delete_photo(db, photo=photo)

    delete_media_file_by_url(url_to_delete)
    if thumb_to_delete:
        delete_media_file_by_url(thumb_to_delete)

    await db.refresh(animal)
    return AnimalWithPhotos.model_validate(animal)
