"""Аутентификация и восстановление пароля (UC-1)."""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import current_user, get_db
from app.api.schemas import EmailIn, LoginIn, ResetIn, user_out
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/login", summary="Вход по логину и паролю (FR-1.1)")
async def login(data: LoginIn, session=Depends(get_db)):
    user, token = await AuthService(session).authenticate(data.login,
                                                          data.password)
    return {"access_token": token, "token_type": "bearer",
            "user": user_out(user)}


@router.post("/token", include_in_schema=False)
async def token(form: OAuth2PasswordRequestForm = Depends(),
                session=Depends(get_db)):
    _, access = await AuthService(session).authenticate(form.username,
                                                        form.password)
    return {"access_token": access, "token_type": "bearer"}


@router.get("/me", summary="Текущий пользователь")
async def me(user=Depends(current_user)):
    return user_out(user)


@router.post("/password-recovery",
             summary="Запрос восстановления пароля (FR-1.3)")
async def password_recovery(data: EmailIn, session=Depends(get_db)):
    await AuthService(session).request_password_reset(data.email)
    return {"detail": "Если адрес зарегистрирован, на него отправлено "
                      "письмо со ссылкой"}


@router.post("/password-reset", summary="Установка нового пароля")
async def password_reset(data: ResetIn, session=Depends(get_db)):
    await AuthService(session).reset_password(data.token, data.new_password)
    return {"detail": "Пароль изменен"}
