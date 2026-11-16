import { reactive } from 'vue'

// 仅保存登录令牌（界面偏好类数据），业务数据全部走接口，不落 localStorage。
const TOKEN_KEY = 'finance_token'

export const session = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
})

export function setToken(token: string) {
  session.token = token
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  session.token = ''
  localStorage.removeItem(TOKEN_KEY)
}
