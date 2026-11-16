<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type Account } from '../api'
import { today } from '../utils'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const formRef = ref()
const saving = ref(false)
const accounts = ref<Account[]>([])

const form = reactive({
  from_id: undefined as number | undefined,
  to_id: undefined as number | undefined,
  amount: undefined as number | undefined,
  date: today(),
  note: '',
})

const fromAccount = computed(() => accounts.value.find((a) => a.id === form.from_id))

const rules = {
  from_id: [{ required: true, message: '请选择转出账户', trigger: 'change' }],
  to_id: [{ required: true, message: '请选择转入账户', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

async function loadAccounts() {
  try {
    const list = await api.accounts.list()
    accounts.value = list.filter((a) => a.enabled)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.from_id = undefined
      form.to_id = undefined
      form.amount = undefined
      form.date = today()
      form.note = ''
      formRef.value?.clearValidate?.()
      loadAccounts()
    }
  },
)

async function submit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (!form.from_id || !form.to_id) return
  if (form.from_id === form.to_id) {
    ElMessage.warning('转出和转入账户不能相同')
    return
  }
  if (!form.amount || form.amount <= 0) {
    ElMessage.warning('请输入大于 0 的金额')
    return
  }
  if (fromAccount.value && fromAccount.value.type !== 'credit' && form.amount > fromAccount.value.balance) {
    ElMessage.warning(`转出账户余额不足（当前 ${fromAccount.value.balance.toFixed(2)}）`)
    return
  }
  saving.value = true
  try {
    await api.accounts.transfer({
      from_id: form.from_id,
      to_id: form.to_id,
      amount: Number(form.amount),
      note: form.note || undefined,
      date: form.date,
    })
    ElMessage.success('划转成功，已生成两条流水')
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
    title="账户划转"
    width="440px"
    :close-on-click-modal="false"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="转出账户" prop="from_id">
        <el-select v-model="form.from_id" placeholder="选择转出账户" style="width: 100%">
          <el-option
            v-for="a in accounts"
            :key="a.id"
            :label="`${a.name}（${a.balance.toFixed(2)}）`"
            :value="a.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="转入账户" prop="to_id">
        <el-select v-model="form.to_id" placeholder="选择转入账户" style="width: 100%">
          <el-option
            v-for="a in accounts"
            :key="a.id"
            :label="a.name"
            :value="a.id"
            :disabled="a.id === form.from_id"
          />
        </el-select>
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
      <el-form-item label="日期" prop="date">
        <el-date-picker
          v-model="form.date"
          type="date"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" maxlength="200" placeholder="可选" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">确认划转</el-button>
    </template>
  </el-dialog>
</template>
