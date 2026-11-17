"""流水记录：查询筛选、新增、编辑、删除、CSV 导出。"""
import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..database import get_db, tx
from ..schemas import TransactionCreate
from .allocation import JAR_SET, allocate_income, clear_allocations, month_of, set_expense_jar

router = APIRouter(prefix='/transactions', tags=['流水'])

TYPE_LABELS = {
    'income': '收入', 'expense': '支出',
    'transfer_out': '划出', 'transfer_in': '划入', 'adjust': '调整',
}


def _today() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def _row_to_item(row) -> dict:
    keys = set(row.keys())
    return {
        'id': row['id'], 'type': row['type'], 'amount': row['amount'],
        'delta': row['delta'],
        'account_id': row['account_id'], 'account_name': row['account_name'],
        'account_type': row['account_type'], 'category': row['category'],
        'note': row['note'], 'date': row['date'], 'created_at': row['created_at'],
        'transfer_group': row['transfer_group'],
        'jar': row['jar'] if 'jar' in keys else None,
    }


_SELECT = ("SELECT t.*, a.name AS account_name, a.type AS account_type, ej.jar AS jar "
           "FROM transactions t JOIN accounts a ON a.id = t.account_id "
           "LEFT JOIN expense_jars ej ON ej.tx_id = t.id")


def _build_where(start, end, account_id, tx_type, category, keyword):
    """组装筛选条件，列表页与 CSV 导出共用。"""
    where, args = [], []
    if start:
        where.append('t.date >= ?'); args.append(start)
    if end:
        where.append('t.date <= ?'); args.append(end)
    if account_id:
        where.append('t.account_id = ?'); args.append(account_id)
    if tx_type:
        where.append('t.type = ?'); args.append(tx_type)
    if category:
        where.append('t.category = ?'); args.append(category)
    if keyword:
        where.append('(t.note LIKE ? OR t.category LIKE ?)')
        args += [f'%{keyword}%', f'%{keyword}%']
    sql = (' WHERE ' + ' AND '.join(where)) if where else ''
    return sql, args


@router.get('')
def list_transactions(
    start: Optional[str] = Query(default=None),
    end: Optional[str] = Query(default=None),
    account_id: Optional[int] = Query(default=None, gt=0),
    tx_type: Optional[str] = Query(default=None, alias='type'),
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    conn = Depends(get_db),
):
    where, args = _build_where(start, end, account_id, tx_type, category, keyword)
    total = conn.execute(f'SELECT COUNT(*) FROM transactions t {where}', args).fetchone()[0]
    rows = conn.execute(
        f'{_SELECT}{where} ORDER BY t.date DESC, t.id DESC LIMIT ? OFFSET ?',
        args + [page_size, (page - 1) * page_size]).fetchall()
    return {'items': [_row_to_item(r) for r in rows], 'total': total,
            'page': page, 'page_size': page_size}


@router.get('/export')
def export_csv(
    start: Optional[str] = Query(default=None),
    end: Optional[str] = Query(default=None),
    account_id: Optional[int] = Query(default=None, gt=0),
    tx_type: Optional[str] = Query(default=None, alias='type'),
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, max_length=50),
    conn = Depends(get_db),
):
    """按当前筛选条件导出 CSV（带 UTF-8 BOM，Excel 打开不乱码）。"""
    where, args = _build_where(start, end, account_id, tx_type, category, keyword)
    rows = conn.execute(
        f'{_SELECT}{where} ORDER BY t.date DESC, t.id DESC', args).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['日期', '类型', '分类', '账户', '金额', '备注'])
    for r in rows:
        signed = r['delta']   # 收入/划入为正，支出/划出为负
        writer.writerow([r['date'], TYPE_LABELS.get(r['type'], r['type']),
                         r['category'] or '未分类', r['account_name'],
                         f'{signed:.2f}', r['note'] or ''])
    filename = f"transactions_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content='\ufeff' + buf.getvalue(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'})


@router.post('', status_code=201)
def create_transaction(body: TransactionCreate, conn = Depends(get_db)):
    acc = conn.execute('SELECT * FROM accounts WHERE id=?', (body.account_id,)).fetchone()
    if not acc:
        raise HTTPException(404, '账户不存在')
    if not acc['enabled']:
        raise HTTPException(400, f"账户「{acc['name']}」已停用")
    if body.jar and body.jar not in JAR_SET:
        raise HTTPException(400, '支出计入的规划账户不存在')
    amt = round(body.amount, 2)
    delta = amt if body.type == 'income' else -amt
    new_bal = round(acc['balance'] + delta, 2)
    if acc['type'] != 'credit' and new_bal < -0.005:
        raise HTTPException(400, f"「{acc['name']}」余额不足（当前 {acc['balance']:.2f}）")
    with tx(conn):
        cur = conn.execute(
            'INSERT INTO transactions(type, amount, delta, account_id, category, note, date) '
            'VALUES(?, ?, ?, ?, ?, ?, ?)',
            (body.type, amt, delta, body.account_id, body.category,
             body.note, body.date))
        conn.execute('UPDATE accounts SET balance=? WHERE id=?', (new_bal, acc['id']))
        txid = cur.lastrowid
        if body.type == 'income':
            # 收入自动按当前分配规则拆分到七个规划账户（零头归 RANDOM）
            allocate_income(conn, txid, amt, month_of(body.date))
        else:
            set_expense_jar(conn, txid, body.jar, month_of(body.date))
    return _row_to_item(conn.execute(
        f'{_SELECT} WHERE t.id=?', (txid,)).fetchone())


@router.put('/{txid}')
def update_transaction(txid: int, body: TransactionCreate, conn = Depends(get_db)):
    old = conn.execute('SELECT * FROM transactions WHERE id=?', (txid,)).fetchone()
    if not old:
        raise HTTPException(404, '流水不存在')
    if old['type'] not in ('income', 'expense'):
        raise HTTPException(400, '转账与调整流水不支持编辑（转账可成对删除）')
    if body.jar and body.jar not in JAR_SET:
        raise HTTPException(400, '支出计入的规划账户不存在')
    acc = conn.execute('SELECT * FROM accounts WHERE id=?', (body.account_id,)).fetchone()
    if not acc:
        raise HTTPException(404, '账户不存在')
    amt = round(body.amount, 2)
    new_delta = amt if body.type == 'income' else -amt
    # 先撤销旧影响，再应用新影响（同一事务里校验）
    old_acc = conn.execute('SELECT * FROM accounts WHERE id=?',
                           (old['account_id'],)).fetchone()
    same_acc = old['account_id'] == body.account_id
    old_bal = round(old_acc['balance'] - old['delta'], 2)   # 原账户撤销后的余额
    if not same_acc and old_acc['type'] != 'credit' and old_bal < -0.005:
        raise HTTPException(400, f"撤销原流水会导致「{old_acc['name']}」余额为负，请先核对")
    new_bal = round(old_bal + new_delta, 2)
    if same_acc and acc['type'] != 'credit' and new_bal < -0.005:
        raise HTTPException(400, f"「{acc['name']}」余额不足（当前 {acc['balance']:.2f}）")
    with tx(conn):
        conn.execute(
            'UPDATE transactions SET type=?, amount=?, delta=?, account_id=?, '
            'category=?, note=?, date=? WHERE id=?',
            (body.type, amt, new_delta, body.account_id, body.category,
             body.note, body.date, txid))
        conn.execute('UPDATE accounts SET balance=? WHERE id=?',
                     (old_bal, old_acc['id']))
        if same_acc:
            conn.execute('UPDATE accounts SET balance=? WHERE id=?',
                         (new_bal, acc['id']))
        else:
            acc_now = conn.execute('SELECT * FROM accounts WHERE id=?',
                                   (acc['id'],)).fetchone()
            final_bal = round(acc_now['balance'] + new_delta, 2)
            if acc['type'] != 'credit' and final_bal < -0.005:
                raise HTTPException(400, f"「{acc['name']}」余额不足")
            conn.execute('UPDATE accounts SET balance=? WHERE id=?',
                         (final_bal, acc['id']))
        # 同步更新分配与额度归属
        clear_allocations(conn, txid)
        set_expense_jar(conn, txid, None, month_of(body.date))
        if body.type == 'income':
            allocate_income(conn, txid, amt, month_of(body.date))
        else:
            set_expense_jar(conn, txid, body.jar, month_of(body.date))
    return _row_to_item(conn.execute(f'{_SELECT} WHERE t.id=?', (txid,)).fetchone())


@router.delete('/{txid}')
def delete_transaction(txid: int, conn = Depends(get_db)):
    old = conn.execute('SELECT * FROM transactions WHERE id=?', (txid,)).fetchone()
    if not old:
        raise HTTPException(404, '流水不存在')
    if old['type'] == 'adjust':
        raise HTTPException(400, '调整流水不支持删除（它用于对齐余额）')
    if old['type'] in ('transfer_out', 'transfer_in'):
        rows = conn.execute('SELECT * FROM transactions WHERE transfer_group=?',
                            (old['transfer_group'],)).fetchall()
    else:
        rows = [old]
    with tx(conn):
        for r in rows:
            acc = conn.execute('SELECT * FROM accounts WHERE id=?',
                               (r['account_id'],)).fetchone()
            if acc:
                new_bal = round(acc['balance'] - r['delta'], 2)
                if acc['type'] != 'credit' and new_bal < -0.005:
                    raise HTTPException(
                        400, f"删除后「{acc['name']}」余额为负，已取消删除")
                conn.execute('UPDATE accounts SET balance=? WHERE id=?',
                             (new_bal, acc['id']))
            conn.execute('DELETE FROM transactions WHERE id=?', (r['id'],))
    return {'message': '已删除'}
