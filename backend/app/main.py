"""个人理财系统 · FastAPI 入口。

启动方式（在 backend 目录下）：
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
监听 0.0.0.0，局域网内其他设备可直连访问。
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth import TOKENS
from .database import init_db
from .routers import accounts, allocation, auth as auth_router, categories, funds, stats, system, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动执行建表脚本 + 种子数据。"""
    init_db()
    yield


app = FastAPI(
    title='个人理财系统',
    description='账户 / 流水 / 分类 / 统计 / 导入导出 / 转账 全套接口。'
                '预留 /api/funds 扩展位用于基金净值自动拉取。',
    lifespan=lifespan,
)

# 跨域：允许前端（含局域网访问的前端 dev 服务）调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 无需令牌的路径
_AUTH_EXEMPT = {'/api/auth/login', '/api/health'}
_DOCS_PREFIX = ('/docs', '/openapi.json', '/redoc')


@app.middleware('http')
async def token_middleware(request: Request, call_next):
    """简单访问控制：除登录/健康检查外，所有接口必须携带有效 X-Token。"""
    path = request.url.path
    if (path.startswith('/api/') and path not in _AUTH_EXEMPT
            and not path.startswith(_DOCS_PREFIX)):
        if request.headers.get('X-Token') not in TOKENS:
            return JSONResponse({'detail': '未登录或登录已过期'},
                                status_code=401)
    return await call_next(request)


@app.get('/api/health')
def health():
    return {'status': 'ok'}


# 业务路由（全部挂载在 /api 下）
app.include_router(auth_router.router, prefix='/api')
app.include_router(accounts.router, prefix='/api')
app.include_router(transactions.router, prefix='/api')
app.include_router(categories.router, prefix='/api')
app.include_router(allocation.router, prefix='/api')
app.include_router(stats.router, prefix='/api')
app.include_router(system.router, prefix='/api')
app.include_router(funds.router, prefix='/api')


if __name__ == '__main__':
    # 兜底：python app/main.py 直接运行
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run('app.main:app' if __package__ else app,
                host='0.0.0.0', port=port)
    sys.exit(0)
