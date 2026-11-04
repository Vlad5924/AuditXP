"""Администрирование учетных записей (UC-7)."""
from fastapi import APIRouter, Depends

from app.api.deps import get_db, require_roles
from app.api.schemas import UserCreate, UserUpdate, user_out
from app.domain.enums import RoleName
from app.repository.user_repository import UserRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Пользователи"])
admin = require_roles(RoleName.ADMIN)


@router.get("", summary="Список учетных записей")
async def list_users(_=Depends(admin), session=Depends(get_db)):
    return [user_out(u) for u in await UserRepository(session).list_all()]


@router.get("/roles", summary="Справочник ролей")
async def roles(_=Depends(admin), session=Depends(get_db)):
    return [{"id": r.id, "name": r.name, "permissions": r.permissions}
            for r in await UserRepository(session).roles()]


@router.post("", status_code=201, summary="Создать учетную запись")
async def create_user(data: UserCreate, actor=Depends(admin),
                      session=Depends(get_db)):
    user = await UserService(session).create(
        login=data.login, full_name=data.full_name, email=data.email,
        password=data.password, role=data.role, actor=actor)
    return user_out(user)


@router.put("/{user_id}", summary="Изменить данные и роль (FR-7.2)")
async def update_user(user_id: int, data: UserUpdate, actor=Depends(admin),
                      session=Depends(get_db)):
    user = await UserService(session).update(
        user_id, actor=actor, full_name=data.full_name, email=data.email,
        role=data.role)
    return user_out(user)


@router.post("/{user_id}/block", summary="Заблокировать (FR-7.1)")
async def block(user_id: int, actor=Depends(admin), session=Depends(get_db)):
    return user_out(await UserService(session).set_locked(user_id, True,
                                                          actor))


@router.post("/{user_id}/unblock", summary="Разблокировать")
async def unblock(user_id: int, actor=Depends(admin),
                  session=Depends(get_db)):
    return user_out(await UserService(session).set_locked(user_id, False,
                                                          actor))


@router.delete("/{user_id}", summary="Удалить (деактивировать)")
async def delete_user(user_id: int, actor=Depends(admin),
                      session=Depends(get_db)):
    return user_out(await UserService(session).deactivate(user_id, actor))
