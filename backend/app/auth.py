"""访问密码与令牌：只有一个访问密码，登录换取令牌，所有接口校验 X-Token。"""
import secrets

# 内存令牌表（服务重启后需重新登录）
TOKENS: set = set()


def create_token() -> str:
    token = secrets.token_hex(16)
    TOKENS.add(token)
    return token


def verify_password(conn, password: str) -> bool:
    row = conn.execute("SELECT value FROM settings WHERE key='access_password'").fetchone()
    if not row:
        return False
    # 常量时间比较，防时序猜测
    return secrets.compare_digest(row['value'], password)


def set_password(conn, password: str) -> None:
    conn.execute(
        "INSERT INTO settings(key, value) VALUES('access_password', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (password,))
