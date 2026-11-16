"""收支分类管理（收入分类 / 支出分类）。"""
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db, tx
from ..schemas import CategoryCreate, CategoryUpdate

router = APIRouter(prefix='/categories', tags=['分类'])


def _to_dict(row) -> dict:
    d = dict(row)
    d['enabled'] = bool(d['enabled'])
    return d


@router.get('')
def list_categories(conn = Depends(get_db)):
    rows = conn.execute('SELECT * FROM categories ORDER BY type, id').fetchall()
    return [_to_dict(r) for r in rows]


@router.post('', status_code=201)
def create_category(body: CategoryCreate, conn = Depends(get_db)):
    try:
        with tx(conn):
            cur = conn.execute(
                'INSERT INTO categories(name, type) VALUES(?, ?)',
                (body.name, body.type))
    except Exception:
        raise HTTPException(409, '同类型下已存在同名分类')
    return _to_dict(conn.execute('SELECT * FROM categories WHERE id=?',
                                 (cur.lastrowid,)).fetchone())


@router.put('/{cid}')
def update_category(cid: int, body: CategoryUpdate, conn = Depends(get_db)):
    old = conn.execute('SELECT * FROM categories WHERE id=?', (cid,)).fetchone()
    if not old:
        raise HTTPException(404, '分类不存在')
    name = body.name.strip() if body.name is not None else old['name']
    if not name:
        raise HTTPException(400, '分类名称不能为空')
    enabled = body.enabled if body.enabled is not None else bool(old['enabled'])
    with tx(conn):
        if name != old['name']:
            exists = conn.execute(
                'SELECT id FROM categories WHERE name=? AND type=? AND id!=?',
                (name, old['type'], cid)).fetchone()
            if exists:
                raise HTTPException(409, '同类型下已存在同名分类')
            # 改名同步到流水，保证历史记录跟着新名字显示
            conn.execute('UPDATE transactions SET category=? WHERE category=? AND type=?',
                         (name, old['name'], old['type']))
        conn.execute('UPDATE categories SET name=?, enabled=? WHERE id=?',
                     (name, int(enabled), cid))
    return _to_dict(conn.execute('SELECT * FROM categories WHERE id=?', (cid,)).fetchone())


@router.delete('/{cid}')
def delete_category(cid: int, conn = Depends(get_db)):
    old = conn.execute('SELECT * FROM categories WHERE id=?', (cid,)).fetchone()
    if not old:
        raise HTTPException(404, '分类不存在')
    with tx(conn):
        # 流水里的分类置空，避免指向已删除分类
        conn.execute('UPDATE transactions SET category=NULL WHERE category=? AND type=?',
                     (old['name'], old['type']))
        conn.execute('DELETE FROM categories WHERE id=?', (cid,))
    return {'message': '分类已删除'}
