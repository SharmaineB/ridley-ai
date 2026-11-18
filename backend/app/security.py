import hashlib
import hmac
import os
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Employee

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(8).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 60000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 60000).hex()
    return hmac.compare_digest(check, digest)


def hash_code(code: str) -> str:
    return hashlib.sha256(f"{settings.jwt_secret}:{code}".encode()).hexdigest()


def make_token(emp: Employee) -> str:
    payload = {
        "sub": emp.employee_id,
        "role": emp.role,
        "exp": datetime.utcnow() + timedelta(hours=settings.token_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> Employee:
    if cred is None:
        raise HTTPException(401, "Not signed in")
    try:
        data = jwt.decode(cred.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired")
    emp = db.get(Employee, data["sub"])
    if emp is None:
        raise HTTPException(401, "Unknown user")
    return emp


def require(*roles: str):
    def dep(user: Employee = Depends(current_user)) -> Employee:
        if user.role not in roles:
            raise HTTPException(403, "Your role cannot open this resource")
        return user

    return dep
