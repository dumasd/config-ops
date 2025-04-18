<script setup lang="ts">
import { Form, FormSchema } from '@/components/Form'
import { useForm } from '@/hooks/web/useForm'
import { PropType, reactive, watch, ref } from 'vue'
import { WorkspaceItem } from '@/api/admin/types'
import { useValidator } from '@/hooks/web/useValidator'
import { useI18n } from '@/hooks/web/useI18n'

const { required } = useValidator()
const { t } = useI18n()
const props = defineProps({
  currentRow: {
    type: Object as PropType<WorkspaceItem>,
    default: () => undefined
  }
})

const formSchema = ref<FormSchema[]>([
  {
    field: 'name',
    label: t('common.name'),
    component: 'Input'
  },
  {
    field: 'description',
    label: t('userDemo.remark'),
    component: 'Input',
    componentProps: {
      type: 'textarea',
      rows: 3
    }
  },
  {
    field: 'id',
    label: t('common.id'),
    component: 'Input',
    hidden: true
  }
])

const rules = reactive({
  name: [required()]
})

const { formRegister, formMethods } = useForm()
const { setValues, getFormData, getElFormExpose } = formMethods

const submit = async () => {
  const elForm = await getElFormExpose()
  const valid = await elForm?.validate().catch((err) => {
    console.log(err)
  })
  if (valid) {
    const formData = await getFormData()
    return formData
  }
}

watch(
  () => props.currentRow,
  (currentRow) => {
    if (!currentRow) return
    setValues(currentRow)
  },
  {
    deep: true,
    immediate: true
  }
)

defineExpose({
  submit
})
</script>

<template>
  <Form :rules="rules" @register="formRegister" :schema="formSchema" />
</template>
