<script setup lang="ts">
import { Form, FormSchema } from '@/components/Form'
import { useForm } from '@/hooks/web/useForm'
import { PropType, reactive, watch, ref } from 'vue'
import { WorkerItem } from '@/api/admin/types'
import { Descriptions, DescriptionsSchema } from '@/components/Descriptions'
import { useValidator } from '@/hooks/web/useValidator'
import { useI18n } from '@/hooks/web/useI18n'

const { required } = useValidator()
const { t } = useI18n()
const props = defineProps({
  currentRow: {
    type: Object as PropType<WorkerItem>,
    default: () => undefined
  }
})

const detailSchema = ref<DescriptionsSchema[]>([
  {
    field: 'name',
    label: t('common.name')
  },
  {
    field: 'description',
    label: t('userDemo.remark')
  },
  {
    field: 'version',
    label: t('worker.version')
  }
])

const formSchema = ref<FormSchema[]>([
  {
    field: 'url',
    label: t('worker.packageUrl'),
    component: 'Input'
  },
  {
    field: 'username',
    label: t('login.username'),
    component: 'Input'
  },
  {
    field: 'password',
    label: t('login.password'),
    component: 'InputPassword'
  }
])

const rules = reactive({
  url: [required()]
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
  <Descriptions :schema="detailSchema" :data="currentRow || {}" />
  <Form :rules="rules" @register="formRegister" :schema="formSchema" />
</template>
