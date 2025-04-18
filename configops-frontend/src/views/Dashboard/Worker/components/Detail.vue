<script setup lang="ts">
import { PropType, ref } from 'vue'
import { WorkspaceItem } from '@/api/admin/types'
import { Descriptions, DescriptionsSchema } from '@/components/Descriptions'
import { useI18n } from '@/hooks/web/useI18n'

const { t } = useI18n()

defineProps({
  currentRow: {
    type: Object as PropType<WorkspaceItem>,
    default: () => undefined
  }
})

const detailSchema = ref<DescriptionsSchema[]>([
  {
    field: 'name',
    label: t('common.name')
  },
  {
    field: 'secret',
    label: t('common.secret')
  },
  {
    field: 'description',
    label: t('userDemo.remark')
  }
])
</script>

<template>
  <Descriptions :schema="detailSchema" :data="currentRow || {}" />
</template>
