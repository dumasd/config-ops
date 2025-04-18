<script setup lang="tsx">
import { reactive, ref, unref, watch } from 'vue'
import { getWorkerApi, createWorkerApi, editWorkerApi, delteWorkerApi } from '@/api/admin'
import { useUserStoreWithOut } from '@/store/modules/user'
import { useTable } from '@/hooks/web/useTable'
import { useI18n } from '@/hooks/web/useI18n'
import { Table, TableColumn } from '@/components/Table'
import { Search } from '@/components/Search'
import { FormSchema } from '@/components/Form'
import { ContentWrap } from '@/components/ContentWrap'
import Write from './components/Write.vue'
import Detail from './components/Detail.vue'
import { Dialog } from '@/components/Dialog'
import { BaseButton } from '@/components/Button'
import { WorkspaceItem } from '@/api/admin/types'
import { ElTag } from 'element-plus'

const { t } = useI18n()

const id = ref('')

const userStore = useUserStoreWithOut()

const { tableRegister, tableState, tableMethods } = useTable({
  immediate: false,
  fetchDataApi: async () => {
    const res = await getWorkerApi(searchParams.value)
    return {
      list: res.data || [],
      total: res.total
    }
  },
  fetchDelApi: async () => {
    const res = await delteWorkerApi(unref(id))
    return !!res
  }
})

const { dataList, loading, total, currentPage, pageSize } = tableState
const { getList, delList, refresh } = tableMethods

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
    field: 'online',
    label: t('userDemo.status'),
    width: 100,
    slots: {
      default: (data: any) => {
        const row = data.row
        const type = row.online ? 'success' : 'danger'
        const txt = row.online ? t('common.online') : t('common.offline')
        return (
          <ElTag type={type} effect="light">
            {txt}
          </ElTag>
        )
      }
    }
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

const saveLoading = ref(false)
const delLoading = ref(false)

const action = (row: any, type: string) => {
  dialogTitle.value = t(type === 'edit' ? 'exampleDemo.edit' : 'exampleDemo.detail')
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
  const write = unref(writeRef)
  const formData = await write?.submit()
  if (formData) {
    saveLoading.value = true
    if (actionType.value == 'edit') {
      editWorkerApi(formData)
        .then(() => {
          dialogVisible.value = false
          getList()
        })
        .finally(() => {
          saveLoading.value = false
        })
    } else {
      createWorkerApi(formData)
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

const delData = async (row: WorkspaceItem) => {
  id.value = row.id
  delLoading.value = true

  await delList(1).finally(() => {
    delLoading.value = false
  })
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
    <div class="mb-10px">
      <BaseButton type="primary" @click="AddAction">{{ t('exampleDemo.add') }}</BaseButton>
    </div>
    <Table
      :columns="tableColumns"
      :data="dataList"
      :loading="loading"
      :pagination="{
        total
      }"
      @register="tableRegister"
    />
  </ContentWrap>

  <Dialog v-model="dialogVisible" :title="dialogTitle">
    <Write v-if="actionType !== 'detail'" ref="writeRef" :current-row="currentRow" />
    <Detail v-else :current-row="currentRow" />

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
