from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_current_user
from ..models import User, Animal
from ..schemas import AnimalWithPhotos, AnimalCreateRequest, AnimalUpdateRequest
from ..repositories.animal_repository import (
    create_animal,
    get_animal_by_id,
    list_animals_for_owner,
    update_animal,
    delete_animal,
)

router = APIRouter(prefix="/animals", tags=["animals"])


@router.get("", response_model=List[AnimalWithPhotos])
async def list_my_animals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AnimalWithPhotos]:
    animals = await list_animals_for_owner(db, owner_user_id=current_user.id)
    return [AnimalWithPhotos.model_validate(a) for a in animals]


@router.post("", response_model=AnimalWithPhotos, status_code=status.HTTP_201_CREATED)
async def create_my_animal(
    payload: AnimalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await create_animal(
        db,
        owner_user_id=current_user.id,
        payload=payload,
    )
    return AnimalWithPhotos.model_validate(animal)


@router.get("/{animal_id}", response_model=AnimalWithPhotos)
async def get_animal(
    animal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await get_animal_by_id(db, animal_id=animal_id)
    if animal is None or animal.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return AnimalWithPhotos.model_validate(animal)


@router.put("/{animal_id}", response_model=AnimalWithPhotos)
async def update_my_animal(
    animal_id: int,
    payload: AnimalUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnimalWithPhotos:
    animal = await get_animal_by_id(db, animal_id=animal_id)
    if animal is None or animal.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    animal = await update_animal(db, animal=animal, payload=payload)
    return AnimalWithPhotos.model_validate(animal)


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_animal(
    animal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    animal = await get_animal_by_id(db, animal_id=animal_id)
    if animal is None or animal.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await delete_animal(db, animal=animal)
