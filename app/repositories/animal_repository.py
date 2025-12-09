from typing import List, Optional

from sqlalchemy import select, and_, exists
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

async def change_animal_status(
    db: AsyncSession,
    *,
    animal: Animal,
    new_status: str,
) -> Animal:
    animal.status = new_status
    await db.commit()
    await db.refresh(animal, attribute_names=["photos"])
    return animal


async def delete_animal(
    db: AsyncSession,
    animal: Animal,
) -> None:
    await db.delete(animal)
    await db.commit()

async def list_public_animals(
    db: AsyncSession,
    *,
    species: Optional[str] = None,
    city: Optional[str] = None,
    sex: Optional[str] = None,
    age_from_years: Optional[int] = None,
    age_to_years: Optional[int] = None,
    has_photos: Optional[bool] = None,
    status: Optional[str] = "active",
    limit: int = 50,
    offset: int = 0,
    order_by: str = "created_at_desc",
) -> List[Animal]:
    """
    Возвращает список животных для публичного фида с фильтрами и пагинацией.
    Фильтрация по возрасту использует поля approx_age_years.
    """

    stmt = select(Animal).options(selectinload(Animal.photos))
    conditions = []

    if status:
        conditions.append(Animal.status == status)

    if species:
        conditions.append(Animal.species == species)

    if city:
        # При необходимости можно заменить на ilike для нечувствительного поиска
        conditions.append(Animal.city == city)

    if sex:
        conditions.append(Animal.sex == sex)

    if age_from_years is not None:
        conditions.append(Animal.approx_age_years >= age_from_years)

    if age_to_years is not None:
        conditions.append(Animal.approx_age_years <= age_to_years)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    if has_photos is not None:
        photos_exists = exists().where(AnimalPhoto.animal_id == Animal.id)
        if has_photos:
            stmt = stmt.where(photos_exists)
        else:
            stmt = stmt.where(~photos_exists)

    if order_by == "created_at_asc":
        stmt = stmt.order_by(Animal.created_at.asc())
    elif order_by == "updated_at_desc":
        stmt = stmt.order_by(Animal.updated_at.desc())
    elif order_by == "updated_at_asc":
        stmt = stmt.order_by(Animal.updated_at.asc())
    else:
        # По умолчанию: новые сначала
        stmt = stmt.order_by(Animal.created_at.desc())

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
