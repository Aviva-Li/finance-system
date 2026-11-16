<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type MonthPoint, type NameValue } from '../api'
import { currentMonth, currentYear, money } from '../utils'
import EChart from '../components/EChart.vue'

const loading = ref(false)
const year = ref(currentYear())
const month = ref<number | 'all'>('all')
const summary = ref({ income: 0, expense: 0, net: 0 })
const pie = ref<NameValue[]>([])
const rankType = ref<'expense' | 'income'>('expense')
const rankData = ref<NameValue[]>([])
const monthly = ref<MonthPoint[]>([])

const years = computed(() => {
  const y = currentYear()
  return [y, y - 1, y - 2, y - 3, y - 4]
})

const months = Array.from({ length: 12 }, (_, i) => i + 1)

const periodLabel = computed(() =>
  month.value === 'all' ? `${year.value} 年全年` : `${year.value} 年 ${month.value} 月`,
)

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
      name: '支出',
      type: 'pie',
      radius: ['44%', '68%'],
      center: ['36%', '50%'],
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: pie.value,
    },
  ],
}))

const rankOption = computed(() => {
  const list = [...rankData.value].reverse()
  const color = rankType.value === 'expense' ? '#d99b8f' : '#5b8c7b'
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: number) => `¥ ${money(v)}` },
    grid: { left: 8, right: 70, top: 12, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#eef2f0' } },
      axisLabel: { color: '#7b8a85' },
    },
    yAxis: {
      type: 'category',
      data: list.map((i) => i.name),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: '#51625d', fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: list.map((i) => i.value),
        barWidth: 14,
        itemStyle: { color, borderRadius: [0, 5, 5, 0] },
        label: {
          show: true,
          position: 'right',
          color: '#51625d',
          fontSize: 11,
          formatter: (p: any) => money(p.value),
        },
      },
    ],
  }
})

const monthlyOption = computed(() => ({
  color: ['#2f9e6e', '#d9635f'],
  tooltip: { trigger: 'axis', valueFormatter: (v: number) => `¥ ${money(v)}` },
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
      type: 'bar',
      barMaxWidth: 14,
      itemStyle: { color: '#79b79c', borderRadius: [4, 4, 0, 0] },
      data: monthly.value.map((m) => m.income),
    },
    {
      name: '支出',
      type: 'bar',
      barMaxWidth: 14,
      itemStyle: { color: '#e3a49f', borderRadius: [4, 4, 0, 0] },
      data: monthly.value.map((m) => m.expense),
    },
  ],
}))

async function loadPeriod() {
  loading.value = true
  try {
    const m = month.value === 'all' ? undefined : month.value
    const [s, p, rank] = await Promise.all([
      api.stats.summary(year.value, m),
      api.stats.pie(year.value, m),
      api.stats.rank({ type: rankType.value, by: 'category', year: year.value, month: m }),
    ])
    summary.value = s
    pie.value = p
    rankData.value = rank
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function loadRank() {
  try {
    const m = month.value === 'all' ? undefined : month.value
    rankData.value = await api.stats.rank({
      type: rankType.value,
      by: 'category',
      year: year.value,
      month: m,
    })
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function loadMonthly() {
  try {
    monthly.value = await api.stats.monthly(year.value)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

watch([year, month], () => {
  loadPeriod()
})

watch(year, () => {
  loadMonthly()
})

watch(rankType, loadRank)

onMounted(() => {
  loadPeriod()
  loadMonthly()
})
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="card">
      <div class="toolbar report-toolbar">
        <el-select v-model="year" style="width: 108px">
          <el-option v-for="y in years" :key="y" :label="`${y} 年`" :value="y" />
        </el-select>
        <el-select v-model="month" style="width: 116px">
          <el-option label="全年" value="all" />
          <el-option v-for="m in months" :key="m" :label="`${m} 月`" :value="m" />
        </el-select>
        <span class="muted">统计区间：{{ periodLabel }}</span>
      </div>

      <div class="report-summary">
        <div class="rs-item">
          <div class="rs-label">收入</div>
          <div class="rs-value positive">+{{ money(summary.income) }}</div>
        </div>
        <div class="rs-item">
          <div class="rs-label">支出</div>
          <div class="rs-value negative">-{{ money(summary.expense) }}</div>
        </div>
        <div class="rs-item">
          <div class="rs-label">结余</div>
          <div class="rs-value" :class="summary.net >= 0 ? 'positive' : 'negative'">
            {{ summary.net >= 0 ? '+' : '-' }}{{ money(Math.abs(summary.net)) }}
          </div>
        </div>
        <div class="rs-item">
          <div class="rs-label">结余率</div>
          <div class="rs-value">
            {{ summary.income > 0 ? Math.round((summary.net / summary.income) * 100) + '%' : '—' }}
          </div>
        </div>
      </div>
    </div>

    <div class="grid-2 section-gap">
      <div class="card">
        <div class="card-title">支出分类占比</div>
        <EChart v-if="pie.length" :option="pieOption" height="310px" />
        <el-empty v-else description="该区间暂无支出" :image-size="80" />
      </div>

      <div class="card">
        <div class="card-title">
          <span>{{ rankType === 'expense' ? '支出' : '收入' }}排行</span>
          <el-radio-group v-model="rankType" size="small">
            <el-radio-button value="expense">支出</el-radio-button>
            <el-radio-button value="income">收入</el-radio-button>
          </el-radio-group>
        </div>
        <EChart v-if="rankData.length" :option="rankOption" height="310px" />
        <el-empty v-else description="该区间暂无数据" :image-size="80" />
      </div>
    </div>

    <div class="card section-gap">
      <div class="card-title">{{ year }} 年各月收支</div>
      <EChart :option="monthlyOption" height="300px" />
    </div>
  </div>
</template>

<style scoped>
.report-toolbar {
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--line);
}

.report-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  padding-top: 16px;
}

.rs-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}

.rs-value {
  font-size: 21px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 760px) {
  .report-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .rs-value {
    font-size: 18px;
  }
}
</style>
