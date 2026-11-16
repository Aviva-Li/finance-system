<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, type Category } from '../api'

const loading = ref(false)
const categories = ref<Category[]>([])
const newName = reactive({ income: '', expense: '' })
const adding = reactive({ income: false, expense: false })

const incomeList = computed(() => categories.value.filter((c) => c.type === 'income'))
const expenseList = computed(() => categories.value.filter((c) => c.type === 'expense'))

async function load() {
  loading.value = true
  try {
    categories.value = await api.categories.list()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function add(type: 'income' | 'expense') {
  const name = newName[type].trim()
  if (!name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  adding[type] = true
  try {
    await api.categories.create({ name, type })
    newName[type] = ''
    ElMessage.success('分类已添加')
    await load()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    adding[type] = false
  }
}

async function rename(row: Category) {
  try {
    const res = await ElMessageBox.prompt('修改分类名称，历史流水会同步更新', '编辑分类', {
      inputValue: row.name,
      inputPattern: /\S+/,
      inputErrorMessage: '名称不能为空',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    const name = String(res.value || '').trim()
    if (!name || name === row.name) return
    await api.categories.update(row.id, { name })
    ElMessage.success('分类已更新')
    await load()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '操作已取消')
  }
}

async function toggle(row: Category, value: boolean) {
  try {
    await api.categories.update(row.id, { enabled: value })
    row.enabled = value
    ElMessage.success(value ? '分类已启用' : '分类已停用')
  } catch (e: any) {
    row.enabled = !value
    ElMessage.error(e.message)
  }
}

async function remove(row: Category) {
  try {
    await ElMessageBox.confirm(
      `删除分类「${row.name}」后，已有流水的该分类会显示为「未分类」，确定继续？`,
      '删除分类',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await api.categories.remove(row.id)
    ElMessage.success('分类已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="cats-grid">
      <div v-for="block in [
        { type: 'expense' as const, title: '支出分类', list: expenseList, hint: '日常消费、生活支出等' },
        { type: 'income' as const, title: '收入分类', list: incomeList, hint: '工资、奖金、投资收益等' },
      ]" :key="block.type" class="card">
        <div class="card-title">
          <span>{{ block.title }}</span>
          <span class="muted">{{ block.list.length }} 个</span>
        </div>

        <div class="add-row">
          <el-input
            v-model="newName[block.type]"
            :placeholder="`新增${block.title}`"
            maxlength="30"
            @keyup.enter="add(block.type)"
          />
          <el-button type="primary" :loading="adding[block.type]" @click="add(block.type)">
            <el-icon class="icon"><Plus /></el-icon>添加
          </el-button>
        </div>

        <div class="cat-list">
          <div v-for="c in block.list" :key="c.id" class="cat-item" :class="{ disabled: !c.enabled }">
            <div class="cat-name">
              {{ c.name }}
              <span v-if="!c.enabled" class="off">已停用</span>
            </div>
            <div class="cat-actions">
              <el-switch
                :model-value="c.enabled"
                size="small"
                @update:model-value="(v: boolean) => toggle(c, v)"
              />
              <el-button link type="primary" size="small" @click="rename(c)">改名</el-button>
              <el-button link type="danger" size="small" @click="remove(c)">删除</el-button>
            </div>
          </div>
          <el-empty
            v-if="!block.list.length"
            :description="`暂无${block.title}`"
            :image-size="60"
          />
        </div>

        <div class="muted foot-hint">{{ block.hint }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.add-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 60px;
}

.cat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fcfdfc;
}

.cat-item.disabled {
  opacity: 0.6;
}

.cat-name {
  font-size: 14px;
}

.off {
  margin-left: 6px;
  font-size: 11px;
  color: var(--muted);
}

.cat-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.icon {
  margin-right: 3px;
}

.foot-hint {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
}

@media (max-width: 900px) {
  .cats-grid {
    grid-template-columns: 1fr;
  }

  .add-row {
    flex-wrap: nowrap;
  }
}
</style>
