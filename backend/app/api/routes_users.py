from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.users import create_user, list_users

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    display_name: str | None = None


@router.post("/users")
def create_user_route(body: UserCreate, db: Session = Depends(get_db)):
    try:
        user_id = create_user(db, body.username, body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"id": user_id, "username": body.username, "display_name": body.display_name or body.username}


@router.get("/users")
def list_users_route(db: Session = Depends(get_db)):
    rows = list_users(db)
    return [{"id": u.id, "username": u.username, "display_name": u.display_name} for u in rows]
