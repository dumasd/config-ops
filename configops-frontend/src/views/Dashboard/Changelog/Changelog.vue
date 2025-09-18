<script setup lang="tsx">
import { reactive, ref, unref, watch } from 'vue'
import { useUserStoreWithOut } from '@/store/modules/user'
import { getManagedObjectsApi, getChangelogsApi, deleteChangelogsApi, updateChangelogsApi } from '@/api/dashboard'
import { ManagedObjectItem, ChangelogItem } from '@/api/dashboard/types'
import { useTable } from '@/hooks/web/useTable'
import { useI18n } from '@/hooks/web/useI18n'
import { Table, TableColumn } from '@/components/Table'
import { Search } from '@/components/Search'
import { FormSchema } from '@/components/Form'
import { ContentWrap } from '@/components/ContentWrap'
import { useValidator } from '@/hooks/web/useValidator'
import { BaseButton } from '@/components/Button'
import Changeset from './components/Changeset.vue'
import { Dialog } from '@/components/Dialog'
import { ElOption, FormRules, ElMessage } from 'element-plus'

const { t } = useI18n()

const { required } = useValidator()

const { tableRegister, tableState, tableMethods } = useTable({
  immediate: false,
  fetchDataApi: async () => {
    const res = await getChangelogsApi({
      page: currentPage.value,
      size: pageSize.value,
      ...unref(searchParams)
    })
    return {
      list: res.data || [],
      total: res.total
    }
  },
  fetchDelApi: async () => {
    const res = await deleteChangelogsApi(currentObjectId.value, unref(deleteRows))
    return !!res
  }
})

const userStore = useUserStoreWithOut()

const { dataList, loading, total, currentPage, pageSize } = tableState
const { getList, delList, getElTableExpose } = tableMethods

const currentObjectId = ref('')
const deleteRows = ref<ChangelogItem[]>([])

const delData = async (row?: ChangelogItem) => {
  const elTableExpose = await getElTableExpose()
  deleteRows.value = row
    ? [row]
    : elTableExpose?.getSelectionRows().map((v: ChangelogItem) => v) || []
  delLoading.value = true

  await delList(unref(deleteRows).length).finally(() => {
    delLoading.value = false
  })
}

const tableColumns = reactive<TableColumn[]>([
  {
    field: 'selection',
    type: 'selection',
    selectable: () => {
      return true
    }
  },
  {
    field: 'change_set_id',
    label: t('changelog.changeSetId'),
    width: 240
  },
  {
    field: 'exectype',
    label: t('changelog.execStatus'),
    width: 120
  },
  {
    field: 'execute_date',
    label: t('changelog.execDate'),
    width: 170
  },
  {
    field: 'filename',
    label: t('changelog.filename')
  },
  {
    field: 'checksum',
    label: t('changelog.checksum')
  },
  {
    field: 'author',
    label: t('changelog.author'),
    width: 100,
  },
  {
    field: 'comment',
    label: t('changelog.comment')
  },
  {
    field: 'action',
    label: t('userDemo.action'),
    width: 300,
    slots: {
      default: (data: any) => {
        const row = data.row
        // 获取当前选中的 managed_object 的 system_type
        return (
          <>
            <BaseButton type="success" onClick={() => action(row, 'detail')}>
              {t('exampleDemo.detail')}
            </BaseButton>
            <BaseButton type="danger" onClick={() => delData(row)}>
              {t('exampleDemo.del')}
            </BaseButton>
            {row.exectype === 'FAILED' && row.system_type !== 'DATABASE' ? (
              <BaseButton type="warning" onClick={() => skip_change_set(row)}>
                {t('exampleDemo.skip')}
              </BaseButton>
            ) : null}
          </>
        )
      }
    }
  }
])

const searchFormRules: FormRules = {
  managed_object_id: [required()],
}

const searchSchema = reactive<FormSchema[]>([
  {
    field: 'managed_object_id',
    component: 'Select',
    componentProps: {
      style: {
        width: '395px'
      },
      clearable: false,
      slots: {
        default: () => {
          return (
            <>
              {managedObjects.value.map((item) => (
                <ElOption key={item.id} label={item.system_id + ' (' + item.system_type + ') | ' + item.worker_name} value={item.id} >
                  <span style="float: left">{item.system_id + ' (' + item.system_type + ')'}</span>
                  <span
                    style="
                        float: right;
                        color: var(--el-text-color-secondary);
                      "
                  >
                    {item.worker_name}
                  </span>
                </ElOption>
              ))}
            </>
          )
        }
      },
    }
  },
  {
    field: 'q',
    //label: t('role.roleName'),
    component: 'Input'
  },
])

const searchParams = ref({})

const setSearchParams = (data: any) => {
  searchParams.value = data
  currentObjectId.value = data.managed_object_id
  getList()
}

const dialogVisible = ref(false)
const dialogTitle = ref('')

const currentRow = ref()
const actionType = ref('')

const saveLoading = ref(false)
const delLoading = ref(false)

const managedObjects = ref<ManagedObjectItem[]>([])

const action = (row: any, type: string) => {
  dialogTitle.value = t(type === 'edit' ? 'exampleDemo.edit' : 'exampleDemo.detail')
  actionType.value = type
  currentRow.value = row
  dialogVisible.value = true
}

const skip_change_set = (row: any) => {
  const data = [
    {
      change_set_id: row.change_set_id,
      system_id: row.system_id,
      system_type: row.system_type,
      exec_status: 'EXECUTED'
    }
  ]
  updateChangelogsApi(currentObjectId.value, data).then((res) => {
    ElMessage.success(t('common.ok'))
  }).finally(() => {
    getList()
  })
}

const fetchManagedObjects = () => {
  if (userStore.getWorkspace) {
    getManagedObjectsApi('changelog').then((res) => {
      managedObjects.value = res.data
    })
  }
}

watch(
  () => userStore.workspace,
  (newVal, oldVal) => {
    // fetchUserWorkspaces()
    fetchManagedObjects()
  }
)

fetchManagedObjects()
</script>

<template>
  <ContentWrap>
    <Search :schema="searchSchema" :rules="searchFormRules" :showReset="false" @search="setSearchParams" />
    <div class="mb-10px">
      <BaseButton :loading="delLoading" type="danger" @click="delData()">
        {{ t('exampleDemo.del') }}
      </BaseButton>
    </div>
    <Table v-model:pageSize="pageSize" v-model:currentPage="currentPage" :columns="tableColumns"
      node-key="change_set_id" row-key="change_set_id" :data="dataList" :loading="loading" :pagination="{
        total
      }" @register="tableRegister" />
  </ContentWrap>

  <Dialog v-model="dialogVisible" :title="dialogTitle" width="80%" max-height="500px">
    <Changeset :current-row="currentRow" :current-object-id="currentObjectId" />
    <template #footer>
      <BaseButton @click="dialogVisible = false">{{ t('dialogDemo.close') }}</BaseButton>
    </template>
  </Dialog>
</template>
