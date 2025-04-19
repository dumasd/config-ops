<script setup lang="tsx">
import { reactive, ref, unref } from 'vue'
import {
  getWorkspacesApi,
  createWorkspacesApi,
  editWorkspacesApi,
  deleteWorkspacesApi,
  editWorkspacePermissionApi
} from '@/api/admin'
import { useTable } from '@/hooks/web/useTable'
import { useI18n } from '@/hooks/web/useI18n'
import { Table, TableColumn } from '@/components/Table'
import { Search } from '@/components/Search'
import { FormSchema } from '@/components/Form'
import { ContentWrap } from '@/components/ContentWrap'
import Write from './components/Write.vue'
import Detail from './components/Detail.vue'
import Permission from './components/Permission.vue'
import { Dialog } from '@/components/Dialog'
import { BaseButton } from '@/components/Button'
import { WorkspaceItem } from '@/api/admin/types'

const { t } = useI18n()

const id = ref('')

const { tableRegister, tableState, tableMethods } = useTable({
  fetchDataApi: async () => {
    const res = await getWorkspacesApi(searchParams.value)
    return {
      list: res.data || [],
      total: res.total
    }
  },
  fetchDelApi: async () => {
    const res = await deleteWorkspacesApi(unref(id))
    return !!res
  }
})

const { dataList, loading, total, pageSize, currentPage } = tableState
const { getList, delList } = tableMethods

const tableColumns = reactive<TableColumn[]>([
  {
    field: 'index',
    label: t('userDemo.index'),
    type: 'index'
  },
  {
    field: 'name',
    label: t('common.name')
  },
  {
    field: 'created_at',
    label: t('tableDemo.displayTime')
  },
  {
    field: 'description',
    label: t('userDemo.remark')
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
            <BaseButton type="primary" onClick={() => action(row, 'edit')}>
              {t('exampleDemo.edit')}
            </BaseButton>
            <BaseButton type="primary" onClick={() => action(row, 'permission')}>
              {t('permission.name')}
            </BaseButton>
            <BaseButton type="success" onClick={() => action(row, 'detail')}>
              {t('exampleDemo.detail')}
            </BaseButton>
            <BaseButton type="danger" onClick={() => delData(row)}>
              {t('exampleDemo.del')}
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

const writeRef = ref<ComponentRef<typeof Write>>()
const permissionRef = ref<ComponentRef<typeof Permission>>()

const saveLoading = ref(false)
const delLoading = ref(false)

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

const AddAction = () => {
  dialogTitle.value = t('exampleDemo.add')
  currentRow.value = undefined
  dialogVisible.value = true
  actionType.value = ''
}

const save = async () => {
  saveLoading.value = true
  if (actionType.value == 'permission') {
    const formData = unref(permissionRef)?.submit()
    if (formData) {
      editWorkspacePermissionApi(formData.id, formData.groupPermissions)
        .then(() => {
          dialogVisible.value = false
        })
        .finally(() => {
          saveLoading.value = false
        })
    }
  } else {
    const write = unref(writeRef)
    const formData = await write?.submit()
    if (formData) {
      if (actionType.value == 'edit') {
        editWorkspacesApi(formData)
          .then(() => {
            dialogVisible.value = false
            getList()
          })
          .finally(() => {
            saveLoading.value = false
          })
      } else {
        createWorkspacesApi(formData)
          .then(() => {
            dialogVisible.value = false
            getList()
          })
          .finally(() => {
            saveLoading.value = false
          })
      }
    }
  }
}

const delData = async (row: WorkspaceItem) => {
  id.value = row.id
  delLoading.value = true

  await delList(1).finally(() => {
    delLoading.value = false
  })
}
</script>

<template>
  <ContentWrap>
    <Search :schema="searchSchema" @reset="setSearchParams" @search="setSearchParams" />
    <div class="mb-10px">
      <BaseButton type="primary" @click="AddAction">{{ t('exampleDemo.add') }}</BaseButton>
    </div>
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

  <Dialog v-model="dialogVisible" :title="dialogTitle" width="70%">
    <Detail v-if="actionType === 'detail'" :current-row="currentRow" />
    <Permission
      v-else-if="actionType === 'permission'"
      ref="permissionRef"
      :current-row="currentRow"
    />
    <Write v-else ref="writeRef" :current-row="currentRow" />

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
