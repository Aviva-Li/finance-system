"""七账户分配：分配规则、收入自动拆分、月度额度总览、重新分配。

分配规则（沿用单文件版约定）：
- 每笔收入按比例拆到七个规划账户，单个账户金额四舍五入到元；
- 因四舍五入产生的零头（含收入的角分部分）全部归入 RANDOM 随机账户；
- 七个账户只是「规划额度」，与「账户管理」里的实际资金账户相互独立。
"""
import math
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db, tx
from ..schemas import AllocationRulesUpdate

router = APIRouter(prefix='/allocation', tags=['七账户分配'])

# 固定七个规划账户，key 不可增删（比例和名称可改）
JARS_ORDER = ['nec', 'ffa', 'lts', 'play', 'edu', 'give', 'random']
JAR_SET = set(JARS_ORDER)
MONTH_RE = re.compile(r'^\d{4}-\d{2}$')


def month_of(date: str) -> str:
    """从 YYYY-MM-DD 日期取月份（YYYY-MM）。"""
    return date[:7]


def allocate_income(conn, txid: int, amount: float, month: str) -> None:
    """按当前规则把一笔收入拆分写入 allocations（调用方需处于写事务中）。"""
    rules = {r['key']: r['percent'] for r in
             conn.execute('SELECT key, percent FROM allocation_rules')}
    rows = []
    used = 0.0
    for key in JARS_ORDER:
        if key == 'random':
            continue
        amt = float(math.floor(amount * rules.get(key, 0) / 100 + 0.5))  # 四舍五入到元
        used += amt
        rows.append((key, amt))
    rows.append(('random', round(amount - used, 2)))   # 零头（含角分）全部归 RANDOM
    for key, amt in rows:
        conn.execute(
            'INSERT INTO allocations(tx_id, month, jar, amount) VALUES(?, ?, ?, ?)',
            (txid, month, key, amt))


def clear_allocations(conn, txid: int) -> None:
    conn.execute('DELETE FROM allocations WHERE tx_id = ?', (txid,))


def set_expense_jar(conn, txid: int, jar: Optional[str], month: str) -> None:
    """登记/更新支出的额度归属（jar 为空表示不计入任何账户额度）。"""
    conn.execute('DELETE FROM expense_jars WHERE tx_id = ?', (txid,))
    if jar:
        conn.execute(
            'INSERT INTO expense_jars(tx_id, jar, month) VALUES(?, ?, ?)',
            (txid, jar, month))


def _check_month(month: str) -> None:
    if not MONTH_RE.match(month):
        raise HTTPException(400, '月份格式必须是 YYYY-MM')


@router.get('/rules')
def get_rules(conn = Depends(get_db)):
    rows = conn.execute('SELECT key, name, percent, sort FROM allocation_rules ORDER BY sort')
    return [{'key': r['key'], 'name': r['name'], 'percent': r['percent'],
             'sort': r['sort']} for r in rows]


@router.put('/rules')
def update_rules(body: AllocationRulesUpdate, conn = Depends(get_db)):
    seen = set()
    total = 0.0
    for item in body.items:
        if item.key not in JAR_SET:
            raise HTTPException(400, f'未知的规划账户：{item.key}')
        if item.key in seen:
            raise HTTPException(400, f'规划账户重复：{item.key}')
        seen.add(item.key)
        total += item.percent
    missing = JAR_SET - seen
    if missing:
        raise HTTPException(400, f'缺少规划账户：{", ".join(sorted(missing))}')
    if abs(total - 100) > 0.001:
        raise HTTPException(400, f'比例合计必须等于 100%（当前 {total:g}%）')
    with tx(conn):
        for item in body.items:
            conn.execute(
                'UPDATE allocation_rules SET name=?, percent=? WHERE key=?',
                (item.name.strip(), item.percent, item.key))
    return {'message': '分配规则已生效', 'total': 100}


@router.get('/overview')
def overview(month: Optional[str] = Query(default=None), conn = Depends(get_db)):
    """某月的七个账户额度：已分配（来自收入自动拆分）/ 已花 / 剩余。"""
    m = month or datetime.now().strftime('%Y-%m')
    _check_month(m)
    rules = conn.execute('SELECT key, name, percent FROM allocation_rules ORDER BY sort').fetchall()

    allocated = {r['jar']: r['total'] for r in conn.execute(
        'SELECT jar, SUM(amount) AS total FROM allocations WHERE month=? GROUP BY jar', (m,))}
    spent = {r['jar']: r['total'] for r in conn.execute(
        'SELECT ej.jar AS jar, SUM(t.amount) AS total FROM expense_jars ej '
        'JOIN transactions t ON t.id = ej.tx_id '
        'WHERE ej.month=? GROUP BY ej.jar', (m,))}

    jars, alloc_total, spent_total = [], 0.0, 0.0
    for r in rules:
        a = round(allocated.get(r['key'], 0), 2)
        s = round(spent.get(r['key'], 0), 2)
        alloc_total += a
        spent_total += s
        jars.append({'key': r['key'], 'name': r['name'], 'percent': r['percent'],
                     'allocated': a, 'spent': s, 'remaining': round(a - s, 2)})
    return {'month': m, 'jars': jars,
            'allocated_total': round(alloc_total, 2),
            'spent_total': round(spent_total, 2)}


@router.post('/reallocate')
def reallocate(body: dict, conn = Depends(get_db)):
    """按当前规则重新拆分某月全部收入（改过比例后可一键重算）。"""
    m = str(body.get('month') or '')
    _check_month(m)
    with tx(conn):
        conn.execute('DELETE FROM allocations WHERE month=?', (m,))
        rows = conn.execute(
            "SELECT id, amount FROM transactions WHERE type='income' AND date LIKE ?",
            (m + '-%',)).fetchall()
        for r in rows:
            allocate_income(conn, r['id'], r['amount'], m)
    return {'message': f'已按当前规则重新分配 {m} 的 {len(rows)} 笔收入'}
