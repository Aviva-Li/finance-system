"""系统设置：网络地址、JSON 导出/导入、重置、修改访问密码。"""
import re
import socket
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..auth import create_token, set_password, verify_password
from ..database import DEFAULT_CATEGORIES, get_db, tx
from ..schemas import ImportReq, PasswordReq

router = APIRouter(prefix='/system', tags=['系统'])

ACC_TYPES = {'cash', 'bank', 'wechat', 'alipay', 'fund', 'credit'}
TX_TYPES = {'income', 'expense', 'transfer_out', 'transfer_in', 'adjust'}
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def lan_ip() -> str:
    """探测本机局域网 IP（UDP connect 只取本地出口地址，不实际发包）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('223.5.5.5', 53))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith(('127.', '169.254.')):
            return ip
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith(('127.', '169.254.')):
            return ip
    except Exception:
        pass
    return '127.0.0.1'


@router.get('/network')
def network():
    """前端页面用它展示「本机 / 局域网访问地址」。"""
    ip = lan_ip()
    return {
        'lan_ip': ip,
        'frontend_port': 5173,
        'backend_port': 8000,
        'frontend_url': f'http://{ip}:5173',
        'backend_url': f'http://{ip}:8000',
    }


@router.get('/export')
def export(conn = Depends(get_db)):
    """全量数据 JSON 备份（不含访问密码）。"""
    return {
        'version': 2,
        'exported_at': datetime.now().isoformat(timespec='seconds'),
        'accounts': [dict(r) for r in
                     conn.execute('SELECT * FROM accounts ORDER BY id')],
        'categories': [dict(r) for r in
                       conn.execute('SELECT * FROM categories ORDER BY id')],
        'transactions': [dict(r) for r in
                         conn.execute('SELECT * FROM transactions ORDER BY id')],
        'allocation_rules': [dict(r) for r in
                             conn.execute('SELECT * FROM allocation_rules ORDER BY sort')],
        'allocations': [dict(r) for r in
                        conn.execute('SELECT * FROM allocations ORDER BY id')],
        'expense_jars': [dict(r) for r in
                         conn.execute('SELECT * FROM expense_jars')],
    }


def _validate_backup(accounts, categories, transactions):
    """导入前的完整校验，任何脏数据直接 400 并给出原因。"""
    acc_ids = set()
    for a in accounts:
        if not isinstance(a, dict) or not str(a.get('name', '')).strip():
            raise HTTPException(400, '备份中存在没有名称的账户')
        if a.get('type') not in ACC_TYPES:
            raise HTTPException(400, f"账户「{a.get('name')}」类型非法：{a.get('type')}")
        bal = a.get('balance', 0)
        if not isinstance(bal, (int, float)) or isinstance(bal, bool) or bal != bal:
            raise HTTPException(400, f"账户「{a.get('name')}」余额不是数字")
        if not isinstance(a.get('id'), int):
            raise HTTPException(400, '备份缺少账户 id，无法恢复流水关联')
        acc_ids.add(a['id'])
    for c in categories:
        if not isinstance(c, dict) or not str(c.get('name', '')).strip():
            raise HTTPException(400, '备份中存在没有名称的分类')
        if c.get('type') not in ('income', 'expense'):
            raise HTTPException(400, f"分类「{c.get('name')}」类型非法")
    for t in transactions:
        if not isinstance(t, dict):
            raise HTTPException(400, '备份中存在格式错误的流水')
        if t.get('type') not in TX_TYPES:
            raise HTTPException(400, f"流水类型非法：{t.get('type')}")
        amt = t.get('amount')
        if not isinstance(amt, (int, float)) or isinstance(amt, bool) or amt <= 0 or amt != amt:
            raise HTTPException(400, '存在非法金额的流水（金额必须为正数）')
        if t.get('account_id') not in acc_ids:
            raise HTTPException(400, '流水引用了备份中不存在的账户')
        if not isinstance(t.get('date'), str) or not DATE_RE.match(t['date']):
            raise HTTPException(400, f"流水日期非法：{t.get('date')}")
    return acc_ids


def _tx_delta(t: dict) -> float:
    """恢复流水对余额的影响方向（老备份缺 delta 字段时按类型推导）。"""
    if isinstance(t.get('delta'), (int, float)) and not isinstance(t.get('delta'), bool):
        return float(t['delta'])
    if t['type'] in ('income', 'transfer_in'):
        return float(t['amount'])
    if t['type'] in ('expense', 'transfer_out'):
        return -float(t['amount'])
    return 0.0   # adjust 缺 delta 时按 0 处理，导入后可用「调整余额」校准


MONTH_RE = re.compile(r'^\d{4}-\d{2}$')
JARS = {'nec', 'ffa', 'lts', 'play', 'edu', 'give', 'random'}


def _validate_allocation(allocations, expense_jars, tx_ids):
    """校验备份数据里的分配记录与支出额度归属。"""
    for a in allocations:
        if not isinstance(a, dict) or a.get('tx_id') not in tx_ids:
            raise HTTPException(400, '分配记录引用了备份中不存在的流水')
        if a.get('jar') not in JARS:
            raise HTTPException(400, f"分配记录账户非法：{a.get('jar')}")
        if not isinstance(a.get('month'), str) or not MONTH_RE.match(a['month']):
            raise HTTPException(400, f"分配记录月份非法：{a.get('month')}")
        amt = a.get('amount')
        if not isinstance(amt, (int, float)) or isinstance(amt, bool) or amt != amt:
            raise HTTPException(400, '分配记录金额不是数字')
    for e in expense_jars:
        if not isinstance(e, dict) or e.get('tx_id') not in tx_ids:
            raise HTTPException(400, '支出额度归属引用了备份中不存在的流水')
        if e.get('jar') not in JARS:
            raise HTTPException(400, f"支出额度账户非法：{e.get('jar')}")
        if not isinstance(e.get('month'), str) or not MONTH_RE.match(e['month']):
            raise HTTPException(400, f"支出额度月份非法：{e.get('month')}")


@router.post('/import')
def import_data(body: ImportReq, conn = Depends(get_db)):
    """JSON 恢复：整体替换现有数据（单事务，出错全部回滚）。"""
    data = body.data or {}
    accounts = data.get('accounts')
    categories = data.get('categories')
    transactions = data.get('transactions')
    if not (isinstance(accounts, list) and isinstance(categories, list)
            and isinstance(transactions, list)):
        raise HTTPException(400, '备份格式不正确：缺少 accounts / categories / transactions')
    _validate_backup(accounts, categories, transactions)
    tx_ids = {t['id'] for t in transactions if isinstance(t.get('id'), int)}
    if len(tx_ids) != len(transactions):
        raise HTTPException(400, '备份中存在重复的流水 id')
    allocations = data.get('allocations') or []
    expense_jars = data.get('expense_jars') or []
    rules = data.get('allocation_rules') or []
    if not isinstance(allocations, list) or not isinstance(expense_jars, list) \
            or not isinstance(rules, list):
        raise HTTPException(400, '备份数据的分配信息格式不正确')
    _validate_allocation(allocations, expense_jars, tx_ids)
    with tx(conn):
        conn.execute('DELETE FROM allocations')
        conn.execute('DELETE FROM expense_jars')
        conn.execute('DELETE FROM transactions')
        conn.execute('DELETE FROM accounts')
        conn.execute('DELETE FROM categories')
        for a in accounts:
            conn.execute(
                'INSERT INTO accounts(id, name, type, balance, enabled) VALUES(?, ?, ?, ?, ?)',
                (a['id'], str(a['name']).strip(), a['type'],
                 round(float(a.get('balance', 0)), 2), int(bool(a.get('enabled', True)))))
        for c in categories:
            conn.execute(
                'INSERT INTO categories(id, name, type, enabled) VALUES(?, ?, ?, ?)',
                (c['id'], str(c['name']).strip(), c['type'],
                 int(bool(c.get('enabled', True)))))
        for t in transactions:
            conn.execute(
                'INSERT INTO transactions(id, type, amount, delta, account_id, category, note, date, transfer_group) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (t['id'], t['type'], round(float(t['amount']), 2),
                 round(_tx_delta(t), 2), t['account_id'],
                 t.get('category'), t.get('note'), t['date'],
                 t.get('transfer_group')))
        for r in rules:
            if isinstance(r, dict) and r.get('key') in JARS:
                conn.execute(
                    'UPDATE allocation_rules SET name=?, percent=? WHERE key=?',
                    (str(r.get('name') or '').strip()[:30] or r['key'],
                     float(r.get('percent', 0)), r['key']))
        for a in allocations:
            conn.execute(
                'INSERT INTO allocations(tx_id, month, jar, amount) VALUES(?, ?, ?, ?)',
                (a['tx_id'], a['month'], a['jar'], round(float(a['amount']), 2)))
        for e in expense_jars:
            conn.execute(
                'INSERT INTO expense_jars(tx_id, jar, month) VALUES(?, ?, ?)',
                (e['tx_id'], e['jar'], e['month']))
    return {'message': '导入成功', 'counts': {
        'accounts': len(accounts), 'categories': len(categories),
        'transactions': len(transactions), 'allocations': len(allocations)}}


@router.post('/reset')
def reset(conn = Depends(get_db)):
    """重置全部数据：清空账户/流水/分类，恢复默认分类（密码保持不变）。"""
    with tx(conn):
        conn.execute('DELETE FROM allocations')
        conn.execute('DELETE FROM expense_jars')
        conn.execute('DELETE FROM transactions')
        conn.execute('DELETE FROM accounts')
        conn.execute('DELETE FROM categories')
        conn.executemany('INSERT INTO categories(name, type) VALUES(?, ?)',
                         DEFAULT_CATEGORIES)
    return {'message': '已重置全部数据（访问密码与分配规则保持不变）'}


@router.post('/password')
def change_password(body: PasswordReq, conn = Depends(get_db)):
    if not verify_password(conn, body.old_password):
        raise HTTPException(400, '原密码不正确')
    with tx(conn):
        set_password(conn, body.new_password)
    return {'token': create_token(), 'message': '密码已修改'}
