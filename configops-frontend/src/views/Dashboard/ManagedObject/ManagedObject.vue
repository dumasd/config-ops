<script setup lang="tsx">
import { reactive, ref, unref, watch } from 'vue'
import { getManagedObjectApi, editManagedObjectPermissionApi } from '@/api/admin'
import { useUserStoreWithOut } from '@/store/modules/user'
import { useTable } from '@/hooks/web/useTable'
import { useI18n } from '@/hooks/web/useI18n'
import { Table, TableColumn } from '@/components/Table'
import { Search } from '@/components/Search'
import { FormSchema } from '@/components/Form'
import { ContentWrap } from '@/components/ContentWrap'
import Permission from './components/Permission.vue'
import { Dialog } from '@/components/Dialog'
import { BaseButton } from '@/components/Button'

const { t } = useI18n()

const userStore = useUserStoreWithOut()

const { tableRegister, tableState, tableMethods } = useTable({
  fetchDataApi: async () => {
    const res = await getManagedObjectApi(searchParams.value)
    return {
      list: res.data || [],
      total: res.total
    }
  }
})

const { dataList, loading, total, currentPage, pageSize } = tableState
const { getList, refresh } = tableMethods

const tableColumns = reactive<TableColumn[]>([
  {
    field: 'index',
    label: t('userDemo.index'),
    type: 'index'
  },
  {
    field: 'system_id',
    label: t('managedObject.systemId'),
    width: 250
  },
  {
    field: 'system_type',
    label: t('managedObject.systemType'),
    width: 160
  },
  {
    field: 'url',
    label: t('managedObject.url')
  },
  {
    field: 'worker_name',
    label: t('managedObject.workerName')
  },
  {
    field: 'action',
    label: t('userDemo.action'),
    width: 380,
    slots: {
      default: (data: any) => {
        const row = data.row
        return (
          <>
            <BaseButton type="primary" onClick={() => action(row, 'permission')}>
              {t('permission.name')}
            </BaseButton>
          </>
        )
      }
    }
  }
])

const searchSchema = reactive<FormSchema[]>([
  {
    field: 'q',
    //label: t('role.roleName'),
    component: 'Input'
  }
])

const searchParams = ref({ page: 1, size: 10 })
const setSearchParams = (data: any) => {
  searchParams.value = data
  searchParams.value.page = currentPage.value
  searchParams.value.size = pageSize.value
  getList()
}

const dialogVisible = ref(false)
const dialogTitle = ref('')

const currentRow = ref()
const actionType = ref('')

const saveLoading = ref(false)
const delLoading = ref(false)

const permissionRef = ref<ComponentRef<typeof Permission>>()

const action = (row: any, type: string) => {
  if (type === 'permission') {
    dialogTitle.value = t('permission.configuration')
  } else {
    dialogTitle.value = t(type === 'edit' ? 'exampleDemo.edit' : 'exampleDemo.detail')
  }
  actionType.value = type
  currentRow.value = row
  dialogVisible.value = true
}

const save = async () => {
  saveLoading.value = true
  if (actionType.value == 'permission') {
    const formData = unref(permissionRef)?.submit()
    if (formData) {
      editManagedObjectPermissionApi(formData.id, formData.groupPermissions)
        .then(() => {
          dialogVisible.value = false
        })
        .finally(() => {
          saveLoading.value = false
        })
    }
  }
}

watch(
  () => userStore.workspace,
  (newVal, oldVal) => {
    if (userStore.getWorkspace) refresh()
  }
)
if (userStore.getWorkspace) refresh()
</script>

<template>
  <ContentWrap>
    <Search :schema="searchSchema" @reset="setSearchParams" @search="setSearchParams" />
    <!-- <div class="mb-10px">
      <BaseButton type="primary" @click="AddAction">{{ t('exampleDemo.add') }}</BaseButton>
    </div> -->
    <Table
      :columns="tableColumns"
      default-expand-all
      node-key="id"
      :data="dataList"
      :loading="loading"
      :pagination="{
        total
      }"
      @register="tableRegister"
    />
  </ContentWrap>

  <Dialog v-model="dialogVisible" :title="dialogTitle">
    <Permission v-if="actionType === 'permission'" ref="permissionRef" :current-row="currentRow" />
    <template #footer>
      <BaseButton
        v-if="actionType !== 'detail'"
        type="primary"
        :loading="saveLoading"
        @click="save"
      >
        {{ t('exampleDemo.save') }}
      </BaseButton>
      <BaseButton @click="dialogVisible = false">{{ t('dialogDemo.close') }}</BaseButton>
    </template>
  </Dialog>
</template>
