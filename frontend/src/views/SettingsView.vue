<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, downloadBlob, type NetworkInfo } from '../api'
import { setToken } from '../state'

const network = ref<NetworkInfo | null>(null)
const importing = ref(false)
const resetting = ref(false)
const changing = ref(false)
const fileInput = ref<HTMLInputElement>()

const pw = reactive({ old: '', next: '', confirm: '' })

async function loadNetwork() {
  try {
    network.value = await api.system.network()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function exportJson() {
  try {
    const data = await api.system.exportAll()
    const d = new Date()
    const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(
      d.getDate(),
    ).padStart(2, '0')}_${String(d.getHours()).padStart(2, '0')}${String(d.getMinutes()).padStart(
      2,
      '0',
    )}`
    downloadBlob(
      new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }),
      `finance_backup_${stamp}.json`,
    )
    ElMessage.success('备份文件已导出')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

function pickFile() {
  fileInput.value?.click()
}

async function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  let data: any
  try {
    data = JSON.parse(await file.text())
  } catch {
    ElMessage.error('文件不是有效的 JSON 备份')
    return
  }

  try {
    await ElMessageBox.confirm(
      '导入会用备份内容整体替换当前全部账户、分类和流水，此操作不可撤销。建议先导出当前数据留底，是否继续？',
      '导入备份',
      { type: 'warning', confirmButtonText: '确认导入', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  importing.value = true
  try {
    const res = await api.system.importAll(data)
    ElMessage.success(
      `导入成功：账户 ${res.counts.accounts}、分类 ${res.counts.categories}、流水 ${res.counts.transactions}`,
    )
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    importing.value = false
  }
}

async function resetAll() {
  try {
    await ElMessageBox.confirm(
      '将清空全部账户、流水和自定义分类，并恢复默认分类。访问密码保持不变。此操作不可撤销，确定重置？',
      '重置全部数据',
      { type: 'error', confirmButtonText: '确认重置', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  resetting.value = true
  try {
    await api.system.reset()
    ElMessage.success('数据已重置')
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    resetting.value = false
  }
}

async function changePassword() {
  if (!pw.old || !pw.next) {
    ElMessage.warning('请填写原密码与新密码')
    return
  }
  if (pw.next.length < 4) {
    ElMessage.warning('新密码至少 4 位')
    return
  }
  if (pw.next !== pw.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  changing.value = true
  try {
    const res = await api.system.changePassword(pw.old, pw.next)
    setToken(res.token)
    pw.old = ''
    pw.next = ''
    pw.confirm = ''
    ElMessage.success('密码已修改，其他设备需用新密码重新登录')
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    changing.value = false
  }
}

onMounted(loadNetwork)
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-title">网络访问</div>
      <div v-if="network" class="net-grid">
        <div class="net-item">
          <div class="net-label">本机访问</div>
          <div class="net-value">http://localhost:5173</div>
        </div>
        <div class="net-item">
          <div class="net-label">局域网访问（手机 / 其他电脑）</div>
          <div class="net-value highlight">{{ network.frontend_url }}</div>
        </div>
        <div class="net-item">
          <div class="net-label">后端 API 地址</div>
          <div class="net-value">{{ network.backend_url }}</div>
        </div>
        <div class="net-item">
          <div class="net-label">接口文档</div>
          <div class="net-value">{{ network.backend_url }}/docs</div>
        </div>
      </div>

      <div class="net-notes">
        <p>后端已监听 0.0.0.0，同一 WiFi / 局域网内的手机、其他电脑直接输入上面的「局域网访问」地址即可使用。</p>
        <p>如果其他设备打不开，请检查 Windows 防火墙是否放行了 5173 和 8000 端口，并确认设备处于同一网络。</p>
        <p>
          需要外网随时访问时，可把后端部署到云服务器（把前端构建产物一并托管），或使用 frp / ngrok
          等内网穿透工具把本机端口映射到公网。数据始终保存在你自己部署的机器上。
        </p>
      </div>
    </div>

    <div class="grid-2 section-gap">
      <div class="card">
        <div class="card-title">数据备份与恢复</div>
        <p class="muted desc">导出为 JSON 文件保存到本地；导入会用备份整体替换当前数据。</p>
        <div class="btn-row">
          <el-button type="primary" plain @click="exportJson">
            <el-icon class="icon"><Download /></el-icon>导出 JSON 备份
          </el-button>
          <el-button plain :loading="importing" @click="pickFile">
            <el-icon class="icon"><Upload /></el-icon>导入 JSON 恢复
          </el-button>
          <input
            ref="fileInput"
            type="file"
            accept=".json,application/json"
            hidden
            @change="onFileChange"
          />
        </div>
        <div class="danger-zone">
          <div>
            <div class="dz-title">重置全部数据</div>
            <div class="muted">清空账户、流水与自定义分类，恢复默认分类。</div>
          </div>
          <el-button type="danger" plain :loading="resetting" @click="resetAll">重置数据</el-button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">访问密码</div>
        <p class="muted desc">防止局域网内其他人随意打开系统，不做注册登录。</p>
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="原密码">
            <el-input v-model="pw.old" type="password" show-password placeholder="当前访问密码" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="pw.next" type="password" show-password placeholder="至少 4 位" />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="pw.confirm" type="password" show-password placeholder="再次输入" />
          </el-form-item>
        </el-form>
        <el-button type="primary" :loading="changing" @click="changePassword">修改密码</el-button>
      </div>
    </div>

    <div class="card section-gap">
      <div class="card-title">扩展能力</div>
      <div class="ext-row">
        <div>
          <div class="ext-title">基金净值自动拉取（预留）</div>
          <div class="muted">
            后端已预留 /api/funds 扩展接口位，后续可对接基金净值源，自动同步基金账户市值与持仓收益。
          </div>
        </div>
        <el-tag type="info" effect="plain">预留接口</el-tag>
      </div>
    </div>
  </div>
</template>

<style scoped>
.net-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.net-item {
  background: #f8faf9;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
}

.net-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}

.net-value {
  font-size: 14px;
  font-weight: 600;
  word-break: break-all;
  font-variant-numeric: tabular-nums;
}

.net-value.highlight {
  color: var(--primary);
}

.net-notes {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.9;
}

.net-notes p {
  margin: 0;
}

.desc {
  margin: 0 0 14px;
}

.btn-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.icon {
  margin-right: 4px;
}

.danger-zone {
  margin-top: 22px;
  padding: 14px;
  border: 1px solid #f0d7d5;
  background: #fdf7f6;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.dz-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.ext-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.ext-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

@media (max-width: 900px) {
  .net-grid {
    grid-template-columns: 1fr;
  }
}
</style>
