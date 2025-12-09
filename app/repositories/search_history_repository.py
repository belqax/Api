# app/repositories/search_history_repository.py

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSearchHistory


async def log_user_search(
    db: AsyncSession,
    *,
    user_id: int,
    source: str,
    filters: Dict[str, Any],
) -> None:
    """
    Сохраняет факт поиска пользователя с набором фильтров.
    Не бросает исключения при ошибке commit, чтобы не ломать основной поток.
    """
    # Отфильтровывает None
    clean_filters = {k: v for k, v in filters.items() if v is not None}

    history = UserSearchHistory(
        user_id=user_id,
        source=source,
        filters=clean_filters,
    )
    db.add(history)
    try:
        await db.commit()
    except Exception:  # noqa: BLE001
        # Логирует, но не пробрасывает дальше
        import logging

        logging.getLogger(__name__).exception("Не удалось сохранить user search history")
        await db.rollback()
