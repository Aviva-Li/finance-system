<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ACCOUNT_TYPE_LABELS,
  api,
  type Account,
  type AccountType,
} from '../api'
import { money } from '../utils'
import TransferDialog from '../components/TransferDialog.vue'

const loading = ref(false)
const accounts = ref<Account[]>([])
const dialogVisible = ref(false)
const saving = ref(false)
const editing = ref<Account | null>(null)
const formRef = ref()
const transferVisible = ref(false)

const form = reactive({
  name: '',
  type: 'cash' as AccountType,
  balance: 0,
  enabled: true,
})

const types: AccountType[] = ['cash', 'bank', 'wechat', 'alipay', 'fund', 'credit']

const rules = {
  name: [{ required: true, message: '请输入账户名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择账户类型', trigger: 'change' }],
}

const totalAsset = computed(() =>
  accounts.value.filter((a) => a.balance > 0).reduce((s, a) => s + a.balance, 0),
)
const totalLiability = computed(() =>
  Math.abs(accounts.value.filter((a) => a.balance < 0).reduce((s, a) => s + a.balance, 0)),
)

function typeTag(t: AccountType) {
  const map: Record<AccountType, string> = {
    cash: 'info',
    bank: 'primary',
    wechat: 'success',
    alipay: 'primary',
    fund: 'warning',
    credit: 'danger',
  }
  return map[t]
}

async function load() {
  loading.value = true
  try {
    accounts.value = await api.accounts.list()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.type = 'cash'
  form.balance = 0
  form.enabled = true
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

function openEdit(row: Account) {
  editing.value = row
  form.name = row.name
  form.type = row.type
  form.balance = row.balance
  form.enabled = row.enabled
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

async function submit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (!form.name.trim()) {
    ElMessage.warning('账户名称不能为空')
    return
  }
  if (form.type !== 'credit' && form.balance < 0) {
    ElMessage.warning('非信用卡账户余额不能为负；信用卡欠款请选信用卡类型并录负数')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      const diff = Number(form.balance) - editing.value.balance
      if (Math.abs(diff) > 0.005) {
        await ElMessageBox.confirm(
          `余额将从 ${money(editing.value.balance)} 调整为 ${money(form.balance)}，系统会自动生成一条「调整」流水用于对账，是否继续？`,
          '确认修改余额',
          { confirmButtonText: '继续', cancelButtonText: '取消' },
        )
      }
      await api.accounts.update(editing.value.id, {
        name: form.name.trim(),
        type: form.type,
        balance: Number(form.balance),
        enabled: form.enabled,
      })
      ElMessage.success('账户已更新')
    } else {
      await api.accounts.create({
        name: form.name.trim(),
        type: form.type,
        balance: Number(form.balance),
        enabled: form.enabled,
      })
      ElMessage.success('账户已创建')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '操作已取消')
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(row: Account, value: boolean) {
  try {
    await api.accounts.update(row.id, { enabled: value })
    row.enabled = value
    ElMessage.success(value ? '账户已启用' : '账户已停用')
  } catch (e: any) {
    row.enabled = !value
    ElMessage.error(e.message)
  }
}

async function remove(row: Account) {
  try {
    await ElMessageBox.confirm(
      `确定删除账户「${row.name}」吗？已有流水的账户不能删除，可改为停用。`,
      '删除账户',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await api.accounts.remove(row.id)
    ElMessage.success('账户已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="summary-line">
        <div>
          <span class="muted">账户资产合计</span>
          <span class="sum positive">{{ money(totalAsset) }}</span>
        </div>
        <div>
          <span class="muted">负债合计</span>
          <span class="sum negative">{{ money(totalLiability) }}</span>
        </div>
        <div class="grow" />
        <el-button type="primary" @click="openCreate">
          <el-icon class="icon"><Plus /></el-icon>新增账户
        </el-button>
        <el-button plain @click="transferVisible = true">
          <el-icon class="icon"><Sort /></el-icon>账户划转
        </el-button>
      </div>

      <div class="table-wrap">
        <el-table :data="accounts" v-loading="loading" stripe empty-text="暂无账户，请先新增">
          <el-table-column prop="name" label="账户名称" min-width="150" />
          <el-table-column label="类型" width="130">
            <template #default="{ row }">
              <el-tag :type="typeTag(row.type)" effect="light" round size="small">
                {{ ACCOUNT_TYPE_LABELS[row.type as AccountType] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="余额" width="150" align="right">
            <template #default="{ row }">
              <span class="amount" :class="row.balance < 0 ? 'negative' : 'positive'">
                {{ row.balance < 0 ? '-' : '' }}{{ money(Math.abs(row.balance)) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="90" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.enabled"
                @update:model-value="(v: boolean) => toggleEnabled(row, v)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="tips">
        <div>提示：编辑余额会生成一条「调整」流水，保证账户余额与流水记录始终一致。</div>
        <div>停用账户不会影响历史流水，只是不能再用于新记账。</div>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑账户' : '新增账户'"
      width="440px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="账户名称" prop="name">
          <el-input v-model="form.name" maxlength="50" placeholder="例如：招商银行储蓄卡" />
        </el-form-item>
        <el-form-item label="账户类型" prop="type">
          <el-select v-model="form.type" style="width: 100%">
            <el-option v-for="t in types" :key="t" :label="ACCOUNT_TYPE_LABELS[t]" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item :label="editing ? '当前余额（元）' : '期初余额（元）'">
          <el-input-number
            v-model="form.balance"
            :precision="2"
            :controls="false"
            style="width: 100%"
          />
          <div class="field-tip">
            信用卡欠款请选择「信用卡/负债」并填写负数，例如 -3500。
          </div>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <TransferDialog v-model="transferVisible" @saved="load" />
  </div>
</template>

<style scoped>
.summary-line {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  padding-bottom: 16px;
  margin-bottom: 4px;
  border-bottom: 1px dashed var(--line);
}

.sum {
  font-size: 20px;
  font-weight: 600;
  margin-left: 8px;
  font-variant-numeric: tabular-nums;
}

.grow {
  flex: 1;
}

.icon {
  margin-right: 4px;
}

.tips {
  margin-top: 14px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.9;
}

.field-tip {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
</style>
