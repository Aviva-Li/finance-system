<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, type AllocationOverview, type JarRule } from '../api'

const loading = ref(false)
const saving = ref(false)
const now = new Date()
const month = ref(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
)
const rules = ref<JarRule[]>([])
const overview = ref<AllocationOverview | null>(null)

const totalPercent = computed(() =>
  Number(rules.value.reduce((s, r) => s + (Number(r.percent) || 0), 0).toFixed(3)),
)

// 示例：按 10000 元收入预览每个账户能分到多少
const EXAMPLE_INCOME = 10000
function exampleOf(r: JarRule) {
  const amt = Math.floor((EXAMPLE_INCOME * (r.percent || 0)) / 100 + 0.5)
  return amt.toLocaleString('zh-CN')
}

function spentPercent(j: { allocated: number; spent: number }) {
  if (j.allocated <= 0) return j.spent > 0 ? 100 : 0
  return Math.min(100, Math.round((j.spent / j.allocated) * 100))
}

async function loadOverview() {
  overview.value = await api.allocation.overview(month.value)
}

async function load() {
  loading.value = true
  try {
    const [r, ] = await Promise.all([api.allocation.rules(), loadOverview()])
    rules.value = r
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

// 比例合计恰好 100% 时自动保存生效（沿用原单文件版习惯）
let saveTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => rules.value.map((r) => ({ key: r.key, name: r.name, percent: r.percent })),
  (val, old) => {
    if (!old || loading.value) return
    if (JSON.stringify(val) === JSON.stringify(old)) return
    clearTimeout(saveTimer)
    saveTimer = setTimeout(async () => {
      if (totalPercent.value !== 100) return
      saving.value = true
      try {
        await api.allocation.updateRules(rules.value)
        ElMessage.success('分配规则已生效')
        await loadOverview()
      } catch (e: any) {
        ElMessage.error(e.message)
      } finally {
        saving.value = false
      }
    }, 600)
  },
  { deep: true },
)

async function doReallocate() {
  try {
    await ElMessageBox.confirm(
      `将清空 ${month.value} 的分配明细，并按当前比例重新拆分该月全部收入。支出额度归属不受影响，确定继续？`,
      '重新分配',
      { type: 'warning', confirmButtonText: '重新分配', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await api.allocation.reallocate(month.value)
    ElMessage.success(res.message)
    await loadOverview()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <!-- 本月额度总览 -->
    <div class="card">
      <div class="card-title">
        <span>本月额度总览</span>
        <div class="toolbar">
          <el-date-picker
            v-model="month"
            type="month"
            value-format="YYYY-MM"
            :clearable="false"
            style="width: 150px"
            @change="loadOverview"
          />
          <el-button :loading="saving" @click="doReallocate">按当前规则重新分配本月</el-button>
        </div>
      </div>

      <div v-if="overview" class="summary muted">
        {{ overview.month }} 收入已自动分配
        <b class="amount">{{ overview.allocated_total.toFixed(2) }}</b> 元，
        已按额度花掉
        <b class="amount">{{ overview.spent_total.toFixed(2) }}</b> 元
      </div>

      <div v-if="overview" class="jars-grid">
        <div v-for="j in overview.jars" :key="j.key" class="jar-card">
          <div class="jar-head">
            <span class="jar-name">{{ j.name }}</span>
            <span class="jar-pct">{{ j.percent }}%</span>
          </div>
          <div class="big-amount jar-remain" :class="j.remaining < 0 ? 'negative' : 'positive'">
            {{ j.remaining.toFixed(2) }}
          </div>
          <div class="muted jar-sub">
            分配 {{ j.allocated.toFixed(2) }} · 已花 {{ j.spent.toFixed(2) }}
          </div>
          <el-progress
            :percentage="spentPercent(j)"
            :stroke-width="6"
            :show-text="false"
            :color="j.remaining < 0 ? '#d9635f' : '#5b8c7b'"
          />
          <div v-if="j.remaining < 0" class="over-hint">已超出本月额度</div>
        </div>
      </div>

      <div class="muted note-line">
        每笔收入登记后自动按比例拆分到七个规划账户（金额四舍五入到元，零头归
        RANDOM）；记账支出时可选「计入哪个账户额度」，花超会标红提醒。七个账户只是
        规划额度，与「账户管理」里的实际资金账户相互独立。
      </div>
    </div>

    <!-- 分配规则编辑 -->
    <div class="card section-gap">
      <div class="card-title">
        <span>分配规则</span>
        <span :class="totalPercent === 100 ? 'positive' : 'negative'">
          合计 {{ totalPercent }}%{{ totalPercent === 100 ? '（自动保存）' : '（需等于 100%）' }}
        </span>
      </div>

      <div class="rule-list">
        <div v-for="r in rules" :key="r.key" class="rule-row">
          <el-input v-model="r.name" maxlength="30" class="rule-name" />
          <el-input-number
            v-model="r.percent"
            :min="0"
            :max="100"
            :precision="1"
            :step="1"
            :controls="false"
            class="rule-pct"
          />
          <span class="muted">%</span>
          <span class="muted rule-example">收入 10,000 元 → {{ exampleOf(r) }} 元</span>
        </div>
      </div>

      <div class="muted note-line">
        提示：比例改成合计恰好 100% 时自动保存生效；改完后可点上方「重新分配本月」重算。
      </div>
    </div>
  </div>
</template>

<style scoped>
.summary {
  margin-bottom: 14px;
}

.jars-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12px;
}

.jar-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 12px;
  background: #fafcfa;
}

.jar-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 6px;
}

.jar-name {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.jar-pct {
  font-size: 12px;
  color: var(--muted);
  flex: 0 0 auto;
}

.jar-remain {
  margin: 10px 0 2px;
}

.jar-sub {
  margin-bottom: 8px;
}

.over-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--negative);
}

.note-line {
  margin-top: 14px;
  line-height: 1.7;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rule-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rule-name {
  flex: 0 1 280px;
}

.rule-pct {
  flex: 0 0 90px;
}

.rule-example {
  flex: 1 1 auto;
  text-align: right;
}

@media (max-width: 1100px) {
  .jars-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 640px) {
  .jars-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .rule-example {
    display: none;
  }
}
</style>
