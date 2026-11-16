"""请求参数模型（Pydantic）：统一做参数校验，拦截负数金额、空值、脏日期等。"""
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

AccountType = Literal['cash', 'bank', 'wechat', 'alipay', 'fund', 'credit']
TxType = Literal['income', 'expense', 'transfer_out', 'transfer_in', 'adjust']
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _check_date(v: str) -> str:
    if not DATE_RE.match(v):
        raise ValueError('日期格式必须是 YYYY-MM-DD')
    try:
        datetime.strptime(v, '%Y-%m-%d')
    except ValueError:
        raise ValueError('日期不合法')
    return v


class AccountCreate(BaseModel):
    """新增账户。信用卡允许负的期初余额（负数=欠款），其余类型不能为负。"""
    name: str = Field(min_length=1, max_length=50, examples=['招商银行储蓄卡'])
    type: AccountType
    balance: float = Field(default=0, le=1e10)
    enabled: bool = True

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('账户名称不能为空')
        return v.strip()


class AccountUpdate(BaseModel):
    """编辑账户；balance 变化时后端会自动生成一条「调整」流水保证对账。"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    type: Optional[AccountType] = None
    enabled: Optional[bool] = None
    balance: Optional[float] = Field(default=None, le=1e10)


class TransactionCreate(BaseModel):
    """新增/编辑收支流水。"""
    type: Literal['income', 'expense']
    account_id: int = Field(gt=0)
    amount: float = Field(gt=0, le=1e10, examples=[35.5])
    category: str = Field(min_length=1, max_length=50)
    note: Optional[str] = Field(default=None, max_length=200)
    date: str = Field(examples=['2026-11-16'])

    @field_validator('date')
    @classmethod
    def valid_date(cls, v: str) -> str:
        return _check_date(v)

    @field_validator('category')
    @classmethod
    def cat_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('分类不能为空')
        return v.strip()


class TransferCreate(BaseModel):
    """账户划转：原子生成两条流水，保证两边金额一致。"""
    from_id: int = Field(gt=0)
    to_id: int = Field(gt=0)
    amount: float = Field(gt=0, le=1e10)
    note: Optional[str] = Field(default=None, max_length=200)
    date: Optional[str] = None

    @field_validator('date')
    @classmethod
    def valid_date(cls, v: Optional[str]) -> Optional[str]:
        return _check_date(v) if v else v


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    type: Literal['income', 'expense']

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('分类名称不能为空')
        return v.strip()


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=30)
    enabled: Optional[bool] = None


class LoginReq(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class PasswordReq(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=4, max_length=128)


class ImportReq(BaseModel):
    data: dict
