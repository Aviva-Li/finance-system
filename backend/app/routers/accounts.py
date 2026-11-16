"""账户管理 + 账户划转（事务保证不错账）。"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db, tx
from ..schemas import AccountCreate, AccountUpdate, TransferCreate

router = APIRouter(prefix='/accounts', tags=['账户'])


def _today() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def _to_dict(row) -> dict:
    d = dict(row)
    d['enabled'] = bool(d['enabled'])
    return d


def _get_account(conn, aid: int):
    row = conn.execute('SELECT * FROM accounts WHERE id=?', (aid,)).fetchone()
    if not row:
        raise HTTPException(404, '账户不存在')
    return row


def _insert_adjust(conn, aid: int, delta: float, category: str, note: str):
    """插入一条调整流水，让「余额 = 该账户所有流水 delta 之和」始终成立。"""
    conn.execute(
        "INSERT INTO transactions(type, amount, delta, account_id, category, note, date) "
        "VALUES('adjust', ?, ?, ?, ?, ?, ?)",
        (round(abs(delta), 2), round(delta, 2), aid, category, note, _today()))


@router.get('')
def list_accounts(conn = Depends(get_db)):
    rows = conn.execute('SELECT * FROM accounts ORDER BY id').fetchall()
    return [_to_dict(r) for r in rows]


@router.post('', status_code=201)
def create_account(body: AccountCreate, conn = Depends(get_db)):
    if body.type != 'credit' and body.balance < 0:
        raise HTTPException(400, '非信用卡账户的期初余额不能为负数（信用卡欠款请用信用卡类型，欠款录为负数）')
    with tx(conn):
        cur = conn.execute(
            'INSERT INTO accounts(name, type, balance, enabled) VALUES(?, ?, ?, ?)',
            (body.name, body.type, round(body.balance, 2), int(body.enabled)))
        aid = cur.lastrowid
        if abs(body.balance) > 0.005:
            _insert_adjust(conn, aid, body.balance, '期初余额', '账户创建期初余额')
    return _to_dict(_get_account(conn, aid))


@router.put('/{aid}')
def update_account(aid: int, body: AccountUpdate, conn = Depends(get_db)):
    old = _get_account(conn, aid)
    name = body.name.strip() if body.name is not None else old['name']
    if not name:
        raise HTTPException(400, '账户名称不能为空')
    acc_type = body.type if body.type is not None else old['type']
    enabled = body.enabled if body.enabled is not None else bool(old['enabled'])
    balance = round(body.balance if body.balance is not None else old['balance'], 2)
    if acc_type != 'credit' and balance < 0:
        raise HTTPException(400, '非信用卡账户余额不能为负数')
    diff = round(balance - old['balance'], 2)
    with tx(conn):
        conn.execute('UPDATE accounts SET name=?, type=?, enabled=?, balance=? WHERE id=?',
                     (name, acc_type, int(enabled), balance, aid))
        if abs(diff) > 0.005:
            _insert_adjust(conn, aid, diff, '余额调整', '手动调整余额')
    return _to_dict(_get_account(conn, aid))


@router.delete('/{aid}')
def delete_account(aid: int, conn = Depends(get_db)):
    _get_account(conn, aid)
    cnt = conn.execute('SELECT COUNT(*) FROM transactions WHERE account_id=?',
                       (aid,)).fetchone()[0]
    if cnt:
        raise HTTPException(409, f'该账户已有 {cnt} 条流水，不能删除；可在列表中「停用」')
    with tx(conn):
        conn.execute('DELETE FROM accounts WHERE id=?', (aid,))
    return {'message': '账户已删除'}


@router.post('/transfer')
def transfer(body: TransferCreate, conn = Depends(get_db)):
    """账户划转：同一事务里原子生成一出一入两条流水，金额绝不错乱。"""
    if body.from_id == body.to_id:
        raise HTTPException(400, '转出和转入账户不能相同')
    amt = round(body.amount, 2)
    date = body.date or _today()
    group = uuid.uuid4().hex
    with tx(conn):
        f = conn.execute('SELECT * FROM accounts WHERE id=?', (body.from_id,)).fetchone()
        t = conn.execute('SELECT * FROM accounts WHERE id=?', (body.to_id,)).fetchone()
        if not f or not t:
            raise HTTPException(404, '账户不存在')
        if not f['enabled'] or not t['enabled']:
            raise HTTPException(400, '账户已停用，不能参与划转')
        new_f = round(f['balance'] - amt, 2)
        new_t = round(t['balance'] + amt, 2)
        if f['type'] != 'credit' and new_f < -0.005:
            raise HTTPException(400, f"转出账户余额不足（当前 {f['balance']:.2f}）")
        note = body.note or '账户划转'
        conn.execute(
            "INSERT INTO transactions(type, amount, delta, account_id, category, note, date, transfer_group) "
            "VALUES('transfer_out', ?, ?, ?, '账户转账', ?, ?, ?)",
            (amt, -amt, f['id'], note, date, group))
        conn.execute(
            "INSERT INTO transactions(type, amount, delta, account_id, category, note, date, transfer_group) "
            "VALUES('transfer_in', ?, ?, ?, '账户转账', ?, ?, ?)",
            (amt, amt, t['id'], note, date, group))
        conn.execute('UPDATE accounts SET balance=? WHERE id=?', (new_f, f['id']))
        conn.execute('UPDATE accounts SET balance=? WHERE id=?', (new_t, t['id']))
    return {'message': '转账成功', 'transfer_group': group}
