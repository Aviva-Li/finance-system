"""基金模块（预留扩展位）：后续对接基金净值自动拉取，接口先占好位置。"""
from fastapi import APIRouter

router = APIRouter(prefix='/funds', tags=['基金(预留)'])


@router.get('/preview')
def preview():
    """预留扩展接口：后续对接天天基金/蛋卷等净值源，自动更新基金账户市值。"""
    return {
        'status': 'not_implemented',
        'message': '预留扩展接口：后续将自动拉取基金净值，同步基金账户市值与持仓收益',
    }
