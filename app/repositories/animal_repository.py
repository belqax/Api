from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Animal, AnimalPhoto
from ..schemas import AnimalCreateRequest, AnimalUpdateRequest


async def create_animal(
    db: AsyncSession,
    *,
    owner_user_id: int,
    payload: AnimalCreateRequest,
) -> Animal:
    animal = Animal(
        owner_user_id=owner_user_id,
        name=payload.name,
        species=payload.species,
        breed=payload.breed,
        sex=payload.sex,
        date_of_birth=payload.date_of_birth,
        approx_age_years=payload.approx_age_years,
        approx_age_months=payload.approx_age_months,
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        color=payload.color,
        pattern=payload.pattern,
        is_neutered=payload.is_neutered,
        is_vaccinated=payload.is_vaccinated,
        is_chipped=payload.is_chipped,
        chip_number=payload.chip_number,
        temperament_note=payload.temperament_note,
        description=payload.description,
        status=payload.status,
        city=payload.city,
        geo_lat=payload.geo_lat,
        geo_lng=payload.geo_lng,
    )
    db.add(animal)
    await db.commit()
    await db.refresh(animal, attribute_names=["photos"])
    return animal


async def get_animal_by_id(
    db: AsyncSession,
    *,
    animal_id: int,
) -> Optional[Animal]:
    stmt = (
        select(Animal)
        .options(selectinload(Animal.photos))
        .where(Animal.id == animal_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_animals_for_owner(
    db: AsyncSession,
    *,
    owner_user_id: int,
) -> List[Animal]:
    stmt = (
        select(Animal)
        .options(selectinload(Animal.photos))
        .where(Animal.owner_user_id == owner_user_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_animal(
    db: AsyncSession,
    animal: Animal,
    payload: AnimalUpdateRequest,
) -> Animal:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(animal, field, value)
    await db.commit()
    await db.refresh(animal, attribute_names=["photos"])
    return animal


async def delete_animal(
    db: AsyncSession,
    animal: Animal,
) -> None:
    await db.delete(animal)
    await db.commit()
