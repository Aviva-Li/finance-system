"""SQLite 数据库：连接、建表脚本、种子数据（服务启动时自动执行）。"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'finance.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('cash','bank','wechat','alipay','fund','credit')),
  balance REAL NOT NULL DEFAULT 0,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS categories(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('income','expense')),
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE(name, type)
);
CREATE TABLE IF NOT EXISTS transactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL CHECK(type IN ('income','expense','transfer_out','transfer_in','adjust')),
  amount REAL NOT NULL CHECK(amount > 0),
  delta REAL NOT NULL,
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  category TEXT,
  note TEXT,
  date TEXT NOT NULL,
  transfer_group TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS allocation_rules(
  key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  percent REAL NOT NULL DEFAULT 0,
  sort INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS allocations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tx_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
  month TEXT NOT NULL,
  jar TEXT NOT NULL,
  amount REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_alloc_month ON allocations(month);
CREATE INDEX IF NOT EXISTS idx_alloc_tx ON allocations(tx_id);
CREATE TABLE IF NOT EXISTS expense_jars(
  tx_id INTEGER PRIMARY KEY REFERENCES transactions(id) ON DELETE CASCADE,
  jar TEXT NOT NULL,
  month TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ejar_month ON expense_jars(month);
"""

# 首次启动的默认分类（可自行增删）
DEFAULT_CATEGORIES = [
    # 收入分类
    ('工资', 'income'), ('奖金', 'income'), ('兼职', 'income'),
    ('投资收益', 'income'), ('红包', 'income'), ('其他收入', 'income'),
    # 支出分类
    ('餐饮', 'expense'), ('交通', 'expense'), ('购物', 'expense'),
    ('居住', 'expense'), ('日用品', 'expense'), ('医疗', 'expense'),
    ('教育', 'expense'), ('娱乐', 'expense'), ('通讯', 'expense'),
    ('人情往来', 'expense'), ('其他支出', 'expense'),
]

# 首次启动的默认设置
DEFAULT_SETTINGS = {
    'access_password': '123456',   # 默认访问密码，可在「系统设置」里修改
}

# 七账户分配（六罐子）默认规则：key 顺序即展示顺序
DEFAULT_JARS = [
    ('nec', 'NEC 生活必需', 40, 1),
    ('ffa', 'FFA 财务自由', 15, 2),
    ('lts', 'LTS 长期储蓄', 15, 3),
    ('play', 'PLAY 玩乐', 10, 4),
    ('edu', 'EDU 教育', 10, 5),
    ('give', 'GIVE 付出', 5, 6),
    ('random', 'RANDOM 随机', 5, 7),
]


def get_conn() -> sqlite3.Connection:
    """获取数据库连接（每请求一个连接，行结果可按字段名访问）。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')   # 多设备并发读写更稳
    conn.isolation_level = None   # 自动提交模式，写事务由 tx() 显式控制
    return conn


def get_db():
    """FastAPI 依赖：请求结束自动关闭连接。"""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def tx(conn):
    """写事务上下文：BEGIN IMMEDIATE 开始，出错自动回滚，保证金额不错乱。"""
    class _Ctx:
        def __enter__(self):
            conn.execute('BEGIN IMMEDIATE')
            return conn

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                conn.execute('COMMIT')
            else:
                try:
                    conn.execute('ROLLBACK')
                except Exception:
                    pass
            return False

    return _Ctx()


def init_db():
    """启动时自动建表 + 种子数据（幂等，重复执行安全）。"""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        if conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 0:
            conn.executemany(
                'INSERT INTO categories(name, type) VALUES(?, ?)', DEFAULT_CATEGORIES)
        if conn.execute('SELECT COUNT(*) FROM settings').fetchone()[0] == 0:
            conn.executemany(
                'INSERT INTO settings(key, value) VALUES(?, ?)',
                list(DEFAULT_SETTINGS.items()))
        if conn.execute('SELECT COUNT(*) FROM allocation_rules').fetchone()[0] == 0:
            conn.executemany(
                'INSERT INTO allocation_rules(key, name, percent, sort) VALUES(?, ?, ?, ?)',
                DEFAULT_JARS)
    finally:
        conn.close()
