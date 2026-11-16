import { clearToken, session } from './state'

// 默认走 Vite 代理 /api；部署时可设置 VITE_API_BASE 指向后端完整地址。
const BASE = (import.meta.env.VITE_API_BASE as string) || '/api'
export const API_BASE = BASE

export type AccountType = 'cash' | 'bank' | 'wechat' | 'alipay' | 'fund' | 'credit'
export type TxType = 'income' | 'expense' | 'transfer_out' | 'transfer_in' | 'adjust'

export interface Account {
  id: number
  name: string
  type: AccountType
  balance: number
  enabled: boolean
  created_at?: string
}

export interface Category {
  id: number
  name: string
  type: 'income' | 'expense'
  enabled: boolean
}

export interface Transaction {
  id: number
  type: TxType
  amount: number
  delta?: number
  account_id: number
  account_name: string
  account_type: AccountType
  category: string | null
  note: string | null
  date: string
  created_at?: string
  transfer_group?: string | null
}

export interface TxPage {
  items: Transaction[]
  total: number
  page: number
  page_size: number
}

export interface Overview {
  total_asset: number
  total_liability: number
  net_asset: number
  month_income: number
  month_expense: number
}

export interface MonthPoint {
  month: number
  income: number
  expense: number
}

export interface NameValue {
  name: string
  value: number
}

export interface NetworkInfo {
  lan_ip: string
  frontend_port: number
  backend_port: number
  frontend_url: string
  backend_url: string
}

function buildQuery(params?: Record<string, any>) {
  if (!params) return ''
  const sp = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') sp.append(k, String(v))
  })
  const s = sp.toString()
  return s ? `?${s}` : ''
}

function humanizeError(data: any): string {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => (d?.loc ? `${d.loc[d.loc.length - 1]}：${d.msg}` : d?.msg))
      .filter(Boolean)
      .join('；')
  }
  return ''
}

async function request<T>(
  path: string,
  options: { method?: string; body?: any; params?: any } = {},
): Promise<T> {
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (session.token) headers['X-Token'] = session.token

  let res: Response
  try {
    res = await fetch(BASE + path + buildQuery(options.params), {
      method: options.method || 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    throw new Error('无法连接后端服务，请确认后端已启动')
  }

  if (res.status === 401) {
    clearToken()
    if (!location.hash.startsWith('#/login')) location.hash = '#/login'
    throw new Error('登录已失效，请重新登录')
  }

  if (!res.ok) {
    let message = `请求失败（${res.status}）`
    try {
      message = humanizeError(await res.json()) || message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export interface TxQuery {
  start?: string
  end?: string
  account_id?: number | ''
  type?: string
  category?: string
  keyword?: string
  page?: number
  page_size?: number
}

export const api = {
  login: (password: string) =>
    request<{ token: string }>('/auth/login', { method: 'POST', body: { password } }),

  accounts: {
    list: () => request<Account[]>('/accounts'),
    create: (body: Partial<Account>) =>
      request<Account>('/accounts', { method: 'POST', body }),
    update: (id: number, body: Partial<Account>) =>
      request<Account>(`/accounts/${id}`, { method: 'PUT', body }),
    remove: (id: number) => request<{ message: string }>(`/accounts/${id}`, { method: 'DELETE' }),
    transfer: (body: {
      from_id: number
      to_id: number
      amount: number
      note?: string
      date?: string
    }) => request<{ message: string; transfer_group: string }>('/accounts/transfer', {
      method: 'POST',
      body,
    }),
  },

  transactions: {
    list: (params: TxQuery) => request<TxPage>('/transactions', { params }),
    create: (body: {
      type: 'income' | 'expense'
      account_id: number
      amount: number
      category: string
      note?: string
      date: string
    }) => request<Transaction>('/transactions', { method: 'POST', body }),
    update: (id: number, body: {
      type: 'income' | 'expense'
      account_id: number
      amount: number
      category: string
      note?: string
      date: string
    }) => request<Transaction>(`/transactions/${id}`, { method: 'PUT', body }),
    remove: (id: number) => request<{ message: string }>(`/transactions/${id}`, { method: 'DELETE' }),
    exportCsv: async (params: TxQuery) => {
      const res = await fetch(BASE + '/transactions/export' + buildQuery(params), {
        headers: session.token ? { 'X-Token': session.token } : {},
      })
      if (!res.ok) throw new Error('导出失败，请稍后重试')
      const blob = await res.blob()
      const today = new Date()
      const stamp = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(
        today.getDate(),
      ).padStart(2, '0')}`
      downloadBlob(blob, `transactions_${stamp}.csv`)
    },
  },

  categories: {
    list: () => request<Category[]>('/categories'),
    create: (body: { name: string; type: 'income' | 'expense' }) =>
      request<Category>('/categories', { method: 'POST', body }),
    update: (id: number, body: { name?: string; enabled?: boolean }) =>
      request<Category>(`/categories/${id}`, { method: 'PUT', body }),
    remove: (id: number) => request<{ message: string }>(`/categories/${id}`, { method: 'DELETE' }),
  },

  stats: {
    overview: () => request<Overview>('/stats/overview'),
    monthly: (year?: number) => request<MonthPoint[]>('/stats/monthly', { params: { year } }),
    summary: (year?: number, month?: number) =>
      request<{ income: number; expense: number; net: number }>('/stats/summary', {
        params: { year, month },
      }),
    pie: (year?: number, month?: number) =>
      request<NameValue[]>('/stats/pie', { params: { year, month } }),
    assetPie: () => request<NameValue[]>('/stats/asset-pie'),
    rank: (params: {
      type: 'income' | 'expense'
      by?: 'category' | 'account'
      year?: number
      month?: number
    }) => request<NameValue[]>('/stats/rank', { params }),
  },

  system: {
    network: () => request<NetworkInfo>('/system/network'),
    exportAll: () => request<any>('/system/export'),
    importAll: (data: any) =>
      request<{ message: string; counts: any }>('/system/import', { method: 'POST', body: { data } }),
    reset: () => request<{ message: string }>('/system/reset', { method: 'POST' }),
    changePassword: (old_password: string, new_password: string) =>
      request<{ token: string; message: string }>('/system/password', {
        method: 'POST',
        body: { old_password, new_password },
      }),
  },

  funds: {
    preview: () => request<any>('/funds/preview'),
  },
}

export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  cash: '现金',
  bank: '储蓄卡',
  wechat: '微信',
  alipay: '支付宝',
  fund: '基金',
  credit: '信用卡/负债',
}

export const TX_TYPE_LABELS: Record<TxType, string> = {
  income: '收入',
  expense: '支出',
  transfer_out: '划出',
  transfer_in: '划入',
  adjust: '调整',
}
