<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ACCOUNT_TYPE_LABELS,
  api,
  TX_TYPE_LABELS,
  type Account,
  type Category,
  type Transaction,
} from '../api'
import { money } from '../utils'
import TransactionDialog from '../components/TransactionDialog.vue'
import TransferDialog from '../components/TransferDialog.vue'

const loading = ref(false)
const rows = ref<Transaction[]>([])
const total = ref(0)
const accounts = ref<Account[]>([])
const categories = ref<Category[]>([])

const filters = reactive({
  dateRange: [] as string[],
  account_id: '' as number | '',
  type: '',
  category: '',
  keyword: '',
})

const page = ref(1)
const pageSize = ref(20)

const txDialogVisible = ref(false)
const txInitialType = ref<'income' | 'expense'>('expense')
const editItem = ref<Transaction | null>(null)
const transferVisible = ref(false)

const categoryOptions = computed(() => {
  if (filters.type === 'income' || filters.type === 'expense') {
    return categories.value.filter(
      (c) => c.type === filters.type && (c.enabled || c.name === filters.category),
    )
  }
  return categories.value
})

const query = computed(() => ({
  start: filters.dateRange?.[0] || undefined,
  end: filters.dateRange?.[1] || undefined,
  account_id: filters.account_id || undefined,
  type: filters.type || undefined,
  category: filters.category || undefined,
  keyword: filters.keyword.trim() || undefined,
}))

async function load() {
  loading.value = true
  try {
    const res = await api.transactions.list({
      ...query.value,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = res.items
    total.value = res.total
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  try {
    const [accs, cats] = await Promise.all([api.accounts.list(), api.categories.list()])
    accounts.value = accs
    categories.value = cats
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.dateRange = []
  filters.account_id = ''
  filters.type = ''
  filters.category = ''
  filters.keyword = ''
  page.value = 1
  load()
}

watch(
  () => filters.type,
  () => {
    if (filters.category) {
      const cat = categories.value.find((c) => c.name === filters.category)
      if (cat && filters.type && cat.type !== filters.type) filters.category = ''
    }
    search()
  },
)

function typeTag(t: string) {
  if (t === 'income') return 'success'
  if (t === 'expense') return 'danger'
  if (t === 'transfer_in' || t === 'transfer_out') return 'warning'
  return 'info'
}

function signedAmount(row: Transaction) {
  const delta = typeof row.delta === 'number' ? row.delta : 0
  const sign = delta > 0 ? '+' : delta < 0 ? '-' : ''
  return `${sign}${money(Math.abs(delta || row.amount))}`
}

function amountClass(row: Transaction) {
  const delta = typeof row.delta === 'number' ? row.delta : 0
  if (delta > 0) return 'positive'
  if (delta < 0) return 'negative'
  return ''
}

function openCreate(type: 'income' | 'expense') {
  editItem.value = null
  txInitialType.value = type
  txDialogVisible.value = true
}

function openEdit(row: Transaction) {
  if (row.type !== 'income' && row.type !== 'expense') {
    ElMessage.info('划转与调整流水不支持编辑，可直接删除')
    return
  }
  editItem.value = row
  txDialogVisible.value = true
}

async function removeRow(row: Transaction) {
  const isTransfer = row.type === 'transfer_in' || row.type === 'transfer_out'
  try {
    await ElMessageBox.confirm(
      isTransfer
        ? '这是账户划转流水，删除后会同时删除对应的另一条流水并回滚两边余额，确定继续？'
        : `确定删除这条${TX_TYPE_LABELS[row.type]}流水吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await api.transactions.remove(row.id)
    ElMessage.success('已删除')
    if (rows.value.length === 1 && page.value > 1) page.value -= 1
    await Promise.all([load(), loadOptions()])
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function exportCsv() {
  try {
    await api.transactions.exportCsv(query.value)
    ElMessage.success('CSV 已开始下载')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

onMounted(async () => {
  await loadOptions()
  await load()
})
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="toolbar filter-bar">
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          range-separator="至"
          style="width: 250px"
          @change="search"
        />
        <el-select
          v-model="filters.account_id"
          placeholder="全部账户"
          clearable
          style="width: 150px"
          @change="search"
        >
          <el-option
            v-for="a in accounts"
            :key="a.id"
            :label="`${a.name}（${ACCOUNT_TYPE_LABELS[a.type]}）`"
            :value="a.id"
          />
        </el-select>
        <el-select
          v-model="filters.type"
          placeholder="全部类型"
          clearable
          style="width: 130px"
          @change="search"
        >
          <el-option label="收入" value="income" />
          <el-option label="支出" value="expense" />
          <el-option label="划出" value="transfer_out" />
          <el-option label="划入" value="transfer_in" />
          <el-option label="调整" value="adjust" />
        </el-select>
        <el-select
          v-model="filters.category"
          placeholder="全部分类"
          clearable
          filterable
          style="width: 140px"
          @change="search"
        >
          <el-option v-for="c in categoryOptions" :key="c.id" :label="c.name" :value="c.name" />
        </el-select>
        <el-input
          v-model="filters.keyword"
          placeholder="搜索备注 / 分类"
          clearable
          style="width: 180px"
          @keyup.enter="search"
          @clear="search"
        />
        <el-button type="primary" plain @click="search">
          <el-icon class="icon"><Search /></el-icon>查询
        </el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <div class="toolbar actions-bar">
        <div class="actions-left">
          <el-button type="primary" @click="openCreate('income')">
            <el-icon class="icon"><Plus /></el-icon>新增收入
          </el-button>
          <el-button type="danger" plain @click="openCreate('expense')">
            <el-icon class="icon"><Minus /></el-icon>新增支出
          </el-button>
          <el-button plain @click="transferVisible = true">
            <el-icon class="icon"><Sort /></el-icon>账户划转
          </el-button>
        </div>
        <div class="actions-right">
          <el-button plain @click="exportCsv">
            <el-icon class="icon"><Download /></el-icon>导出 CSV
          </el-button>
        </div>
      </div>

      <div class="table-wrap">
        <el-table :data="rows" v-loading="loading" stripe style="width: 100%" empty-text="暂无流水">
          <el-table-column prop="date" label="日期" width="108" />
          <el-table-column label="类型" width="82">
            <template #default="{ row }">
              <el-tag :type="typeTag(row.type)" size="small" effect="light" round>
                {{ TX_TYPE_LABELS[row.type as keyof typeof TX_TYPE_LABELS] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="分类" min-width="96">
            <template #default="{ row }">{{ row.category || '未分类' }}</template>
          </el-table-column>
          <el-table-column label="账户" min-width="120">
            <template #default="{ row }">
              <div class="acc-cell">
                <span>{{ row.account_name }}</span>
                <span class="acc-type">{{ ACCOUNT_TYPE_LABELS[row.account_type as keyof typeof ACCOUNT_TYPE_LABELS] }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="金额" width="130" align="right">
            <template #default="{ row }">
              <span class="amount" :class="amountClass(row)">{{ signedAmount(row) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.note || '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="128" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="removeRow(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="load"
          @size-change="search"
        />
      </div>
    </div>

    <TransactionDialog
      v-model="txDialogVisible"
      :initial-type="txInitialType"
      :edit-item="editItem"
      @saved="loadOptions().then(load)"
    />
    <TransferDialog v-model="transferVisible" @saved="loadOptions().then(load)" />
  </div>
</template>

<style scoped>
.filter-bar {
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--line);
}

.actions-bar {
  justify-content: space-between;
  padding: 14px 0;
}

.actions-left,
.actions-right {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.icon {
  margin-right: 4px;
}

.acc-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}

.acc-type {
  font-size: 11px;
  color: var(--muted);
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

@media (max-width: 700px) {
  .filter-bar :deep(.el-date-editor),
  .filter-bar :deep(.el-select),
  .filter-bar :deep(.el-input) {
    width: 100% !important;
  }

  .toolbar {
    gap: 8px;
  }

  .actions-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .pager {
    justify-content: center;
  }
}
</style>
