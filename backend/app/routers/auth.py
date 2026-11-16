"""登录：只有一个访问密码，换取访问令牌。"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import create_token, verify_password
from ..database import get_db
from ..schemas import LoginReq

router = APIRouter(prefix='/auth', tags=['登录'])


@router.post('/login')
def login(body: LoginReq, conn = Depends(get_db)):
    if not verify_password(conn, body.password):
        raise HTTPException(401, '密码错误')
    return {'token': create_token()}
