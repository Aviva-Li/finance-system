<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ACCOUNT_TYPE_LABELS,
  api,
  type Account,
  type AccountType,
  type MonthPoint,
  type NameValue,
  type Overview,
} from '../api'
import { currentYear, money } from '../utils'
import EChart from '../components/EChart.vue'
import TransactionDialog from '../components/TransactionDialog.vue'
import TransferDialog from '../components/TransferDialog.vue'

const loading = ref(false)
const accounts = ref<Account[]>([])
const overview = ref<Overview>({
  total_asset: 0,
  total_liability: 0,
  net_asset: 0,
  month_income: 0,
  month_expense: 0,
})
const monthly = ref<MonthPoint[]>([])
const assetPie = ref<NameValue[]>([])
const selectedYear = ref(currentYear())

const txDialogVisible = ref(false)
const txInitialType = ref<'income' | 'expense'>('expense')
const transferVisible = ref(false)

const years = computed(() => {
  const y = currentYear()
  return [y, y - 1, y - 2, y - 3, y - 4]
})

const typeCards = computed(() => {
  const types: AccountType[] = ['cash', 'bank', 'wechat', 'alipay', 'fund']
  return types.map((t) => ({
    type: t,
    label: ACCOUNT_TYPE_LABELS[t],
    value: accounts.value.filter((a) => a.type === t).reduce((s, a) => s + a.balance, 0),
  }))
})

const liability = computed(() => {
  const credit = accounts.value
    .filter((a) => a.type === 'credit')
    .reduce((s, a) => s + a.balance, 0)
  return credit < 0 ? Math.abs(credit) : 0
})

const hasAccounts = computed(() => accounts.value.length > 0)

const monthlyOption = computed(() => ({
  color: ['#2f9e6e', '#d9635f'],
  tooltip: {
    trigger: 'axis',
    valueFormatter: (v: number) => `¥ ${money(v)}`,
  },
  legend: { data: ['收入', '支出'], top: 0, textStyle: { color: '#51625d' } },
  grid: { left: 8, right: 18, top: 38, bottom: 4, containLabel: true },
  xAxis: {
    type: 'category',
    data: monthly.value.map((m) => `${m.month}月`),
    axisLine: { lineStyle: { color: '#e3e9e6' } },
    axisTick: { show: false },
    axisLabel: { color: '#7b8a85' },
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#eef2f0' } },
    axisLabel: { color: '#7b8a85' },
  },
  series: [
    {
      name: '收入',
      type: 'line',
      smooth: true,
      symbolSize: 5,
      data: monthly.value.map((m) => m.income),
      areaStyle: { opacity: 0.08 },
    },
    {
      name: '支出',
      type: 'line',
      smooth: true,
      symbolSize: 5,
      data: monthly.value.map((m) => m.expense),
      areaStyle: { opacity: 0.08 },
    },
  ],
}))

const pieOption = computed(() => ({
  color: ['#5b8c7b', '#7fa8c9', '#c9a77f', '#a58fc4', '#8fbf9f', '#d99b8f', '#93a8a0'],
  tooltip: { trigger: 'item', valueFormatter: (v: number) => `¥ ${money(v)}` },
  legend: {
    type: 'scroll',
    orient: 'vertical',
    right: 0,
    top: 'middle',
    itemWidth: 9,
    itemHeight: 9,
    textStyle: { color: '#51625d', fontSize: 12 },
  },
  series: [
    {
      name: '资产分布',
      type: 'pie',
      radius: ['46%', '70%'],
      center: ['36%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: assetPie.value,
    },
  ],
}))

async function load() {
  loading.value = true
  try {
    const [accs, ov, m, pie] = await Promise.all([
      api.accounts.list(),
      api.stats.overview(),
      api.stats.monthly(selectedYear.value),
      api.stats.assetPie(),
    ])
    accounts.value = accs
    overview.value = ov
    monthly.value = m
    assetPie.value = pie
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function loadMonthly() {
  try {
    monthly.value = await api.stats.monthly(selectedYear.value)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

function openTx(type: 'income' | 'expense') {
  txInitialType.value = type
  txDialogVisible.value = true
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="card-grid">
      <div v-for="c in typeCards" :key="c.type" class="asset-card">
        <div class="asset-label">{{ c.label }}</div>
        <div class="asset-value">{{ money(c.value) }}</div>
      </div>
      <div class="asset-card">
        <div class="asset-label">负债</div>
        <div class="asset-value negative">{{ liability > 0 ? '-' : '' }}{{ money(liability) }}</div>
      </div>
    </div>

    <div class="summary card">
      <div class="summary-item">
        <div class="summary-label">总资产</div>
        <div class="summary-value">{{ money(overview.total_asset) }}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">总负债</div>
        <div class="summary-value negative">{{ money(overview.total_liability) }}</div>
      </div>
      <div class="summary-item main">
        <div class="summary-label">净资产</div>
        <div class="big-amount">{{ money(overview.net_asset) }}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">本月收入</div>
        <div class="summary-value positive">+{{ money(overview.month_income) }}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">本月支出</div>
        <div class="summary-value negative">-{{ money(overview.month_expense) }}</div>
      </div>
    </div>

    <div class="quick card">
      <div class="quick-label">快捷记账</div>
      <div class="quick-actions">
        <el-button type="primary" @click="openTx('income')">
          <el-icon class="icon"><Plus /></el-icon>新增收入
        </el-button>
        <el-button type="danger" plain @click="openTx('expense')">
          <el-icon class="icon"><Minus /></el-icon>新增支出
        </el-button>
        <el-button plain @click="transferVisible = true">
          <el-icon class="icon"><Sort /></el-icon>账户划转
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!hasAccounts"
      class="section-gap"
      type="info"
      :closable="false"
      show-icon
      title="还没有账户"
      description="先到「账户管理」添加现金、银行卡等账户，再开始记账。"
    />

    <div class="grid-2 section-gap">
      <div class="card">
        <div class="card-title">
          <span>月度收支趋势</span>
          <el-select v-model="selectedYear" size="small" style="width: 104px" @change="loadMonthly">
            <el-option v-for="y in years" :key="y" :label="`${y} 年`" :value="y" />
          </el-select>
        </div>
        <EChart :option="monthlyOption" height="300px" />
      </div>
      <div class="card">
        <div class="card-title">资产分布</div>
        <EChart v-if="assetPie.length" :option="pieOption" height="300px" />
        <el-empty v-else description="暂无资产数据" :image-size="80" />
      </div>
    </div>

    <TransactionDialog v-model="txDialogVisible" :initial-type="txInitialType" @saved="load" />
    <TransferDialog v-model="transferVisible" @saved="load" />
  </div>
</template>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.asset-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px;
}

.asset-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 8px;
}

.asset-value {
  font-size: 19px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.3px;
}

.summary {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  align-items: center;
}

.summary-item {
  min-width: 0;
}

.summary-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}

.summary-value {
  font-size: 18px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.summary-item.main {
  border-left: 1px solid var(--line);
  border-right: 1px solid var(--line);
  padding: 0 18px;
}

.quick {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 14px;
  font-weight: 600;
}

.quick-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.icon {
  margin-right: 4px;
}

@media (max-width: 1100px) {
  .card-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-item.main {
    grid-column: span 2;
    border-left: none;
    border-right: none;
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    padding: 12px 0;
    order: -1;
  }
}

@media (max-width: 520px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .asset-value {
    font-size: 16px;
  }
}
</style>
