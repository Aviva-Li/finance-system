<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type Account, type Category, type Transaction } from '../api'
import { today } from '../utils'

const props = defineProps<{
  modelValue: boolean
  initialType?: 'income' | 'expense'
  editItem?: Transaction | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const formRef = ref()
const saving = ref(false)
const accounts = ref<Account[]>([])
const categories = ref<Category[]>([])
const loading = ref(false)

const form = reactive({
  type: 'expense' as 'income' | 'expense',
  account_id: undefined as number | undefined,
  amount: undefined as number | undefined,
  category: '',
  note: '',
  date: today(),
})

const title = computed(() => {
  if (props.editItem) return '编辑流水'
  return form.type === 'income' ? '新增收入' : '新增支出'
})

const filteredCategories = computed(() =>
  categories.value.filter((c) => c.type === form.type && c.enabled),
)

const rules = {
  account_id: [{ required: true, message: '请选择账户', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

function resetForm() {
  const item = props.editItem
  if (item) {
    form.type = item.type === 'income' ? 'income' : 'expense'
    form.account_id = item.account_id
    form.amount = item.amount
    form.category = item.category || ''
    form.note = item.note || ''
    form.date = item.date
  } else {
    form.type = props.initialType || 'expense'
    form.account_id = undefined
    form.amount = undefined
    form.category = ''
    form.note = ''
    form.date = today()
  }
  formRef.value?.clearValidate?.()
}

async function loadOptions() {
  loading.value = true
  try {
    const [accs, cats] = await Promise.all([api.accounts.list(), api.categories.list()])
    accounts.value = accs.filter((a) => a.enabled)
    categories.value = cats
    if (!props.editItem && !form.account_id && accounts.value.length === 1) {
      form.account_id = accounts.value[0].id
    }
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      resetForm()
      await loadOptions()
    }
  },
)

watch(
  () => form.type,
  () => {
    if (!filteredCategories.value.some((c) => c.name === form.category)) {
      form.category = filteredCategories.value[0]?.name || ''
    }
  },
)

async function submit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (!form.account_id || !form.amount || form.amount <= 0) {
    ElMessage.warning('请填写正确的账户与金额')
    return
  }
  saving.value = true
  try {
    const body = {
      type: form.type,
      account_id: form.account_id,
      amount: Number(form.amount),
      category: form.category,
      note: form.note || undefined,
      date: form.date,
    }
    if (props.editItem) {
      await api.transactions.update(props.editItem.id, body)
      ElMessage.success('流水已更新')
    } else {
      await api.transactions.create(body)
      ElMessage.success('已记录')
    }
    emit('update:modelValue', false)
    emit('saved')
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="460px"
    :close-on-click-modal="false"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" v-loading="loading">
      <el-form-item label="类型">
        <el-radio-group v-model="form.type" :disabled="!!editItem">
          <el-radio-button value="expense">支出</el-radio-button>
          <el-radio-button value="income">收入</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="金额（元）" prop="amount">
        <el-input-number
          v-model="form.amount"
          :min="0.01"
          :max="1000000000"
          :precision="2"
          :controls="false"
          placeholder="0.00"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="账户" prop="account_id">
        <el-select v-model="form.account_id" placeholder="选择账户" style="width: 100%">
          <el-option
            v-for="a in accounts"
            :key="a.id"
            :label="`${a.name}（余额 ${a.balance.toFixed(2)}）`"
            :value="a.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="分类" prop="category">
        <el-select v-model="form.category" placeholder="选择分类" style="width: 100%">
          <el-option v-for="c in filteredCategories" :key="c.id" :label="c.name" :value="c.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期" prop="date">
        <el-date-picker
          v-model="form.date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" maxlength="200" placeholder="可选，例如：超市采购" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
