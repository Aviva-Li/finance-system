"""统计报表：总览、月度收支、占比饼图、排行（预留基金接口见 funds.py）。"""
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from ..database import get_db

router = APIRouter(prefix='/stats', tags=['统计'])


def _month_prefix() -> str:
    return datetime.now().strftime('%Y-%m')


@router.get('/overview')
def overview(conn = Depends(get_db)):
    """总资产 / 总负债 / 净资产 + 本月收支。负债=负余额绝对值（信用卡欠款等）。"""
    rows = conn.execute('SELECT balance FROM accounts').fetchall()
    asset = round(sum(r['balance'] for r in rows if r['balance'] > 0), 2)
    liability = round(sum(-r['balance'] for r in rows if r['balance'] < 0), 2)
    net = round(asset - liability, 2)
    mp = _month_prefix()
    row = conn.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END),0) AS inc, "
        "COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),0) AS exp "
        "FROM transactions WHERE substr(date,1,7)=?", (mp,)).fetchone()
    return {'total_asset': asset, 'total_liability': liability, 'net_asset': net,
            'month_income': round(row['inc'], 2),
            'month_expense': round(row['exp'], 2)}


@router.get('/monthly')
def monthly(year: Optional[int] = Query(default=None, ge=1970, le=9999),
            conn = Depends(get_db)):
    """按年返回 12 个月的收入 / 支出（未发生的月份补 0）。"""
    y = year or datetime.now().year
    rows = conn.execute(
        "SELECT substr(date,1,7) AS m, "
        "COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END),0) AS inc, "
        "COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),0) AS exp "
        "FROM transactions WHERE substr(date,1,4)=? AND type IN ('income','expense') "
        "GROUP BY m", (str(y),)).fetchall()
    data = {r['m']: r for r in rows}
    out = []
    for m in range(1, 13):
        key = f'{y}-{m:02d}'
        r = data.get(key)
        out.append({'month': m,
                    'income': round(r['inc'], 2) if r else 0,
                    'expense': round(r['exp'], 2) if r else 0})
    return out


@router.get('/summary')
def summary(year: Optional[int] = Query(default=None, ge=1970),
            month: Optional[int] = Query(default=None, ge=1, le=12),
            conn = Depends(get_db)):
    """按年或按月汇总收入 / 支出 / 结余。month 省略 = 全年。"""
    y = year or datetime.now().year
    op, arg = _date_filter(y, month)
    row = conn.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END),0) AS inc, "
        "COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),0) AS exp "
        f"FROM transactions WHERE date {op}", (arg,)).fetchone()
    inc = round(row['inc'], 2)
    exp = round(row['exp'], 2)
    return {'income': inc, 'expense': exp, 'net': round(inc - exp, 2)}


def _date_filter(year: Optional[int], month: Optional[int]):
    """返回 (LIKE 模式, 参数)：month 为空则统计全年。"""
    if month:
        return 'LIKE ?', f'{year}-{month:02d}-%'
    return 'LIKE ?', f'{year}-%'


@router.get('/pie')
def expense_pie(year: Optional[int] = Query(default=None, ge=1970),
                month: Optional[int] = Query(default=None, ge=1, le=12),
                conn = Depends(get_db)):
    """支出按分类占比。month 省略 = 全年。"""
    y = year or datetime.now().year
    op, arg = _date_filter(y, month)
    rows = conn.execute(
        f"SELECT COALESCE(category,'未分类') AS name, SUM(amount) AS value "
        f"FROM transactions WHERE type='expense' AND date {op} "
        f"GROUP BY name ORDER BY value DESC", (arg,)).fetchall()
    return [{'name': r['name'], 'value': round(r['value'], 2)} for r in rows]


@router.get('/asset-pie')
def asset_pie(conn = Depends(get_db)):
    """资产分布（按账户，只统计正余额账户）。"""
    rows = conn.execute(
        'SELECT name, balance FROM accounts WHERE balance > 0.005 ORDER BY balance DESC'
    ).fetchall()
    return [{'name': r['name'], 'value': round(r['balance'], 2)} for r in rows]


@router.get('/rank')
def rank(
    type: Literal['income', 'expense'] = Query(default='expense'),
    by: Literal['category', 'account'] = Query(default='category'),
    year: Optional[int] = Query(default=None, ge=1970),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    conn = Depends(get_db),
):
    """收入 / 支出排行，可按分类或按账户。"""
    y = year or datetime.now().year
    op, arg = _date_filter(y, month)
    if by == 'category':
        key = "COALESCE(t.category,'未分类')"
        join = ''
    else:
        key = 'a.name'
        join = ' JOIN accounts a ON a.id = t.account_id'
    rows = conn.execute(
        f"SELECT {key} AS name, SUM(t.amount) AS value "
        f"FROM transactions t{join} "
        f"WHERE t.type=? AND t.date {op} "
        f"GROUP BY name ORDER BY value DESC LIMIT 20", (type, arg)).fetchall()
    return [{'name': r['name'], 'value': round(r['value'], 2)} for r in rows]
