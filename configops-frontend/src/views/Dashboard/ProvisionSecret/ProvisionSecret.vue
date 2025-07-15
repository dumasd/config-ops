<script setup lang="tsx">
import { reactive, ref, unref, watch } from 'vue'
import { useUserStoreWithOut } from '@/store/modules/user'
import { getManagedObjectsApi, getSecretsApi } from '@/api/dashboard'
import { ManagedObjectItem } from '@/api/dashboard/types'
import { useTable } from '@/hooks/web/useTable'
import { useI18n } from '@/hooks/web/useI18n'
import { Table, TableColumn } from '@/components/Table'
import { Search } from '@/components/Search'
import { FormSchema } from '@/components/Form'
import { ContentWrap } from '@/components/ContentWrap'
import { PasswordDisplay } from '@/components/PasswordDisplay'
import { useValidator } from '@/hooks/web/useValidator'
import { ElOption, FormRules } from 'element-plus'

const { t } = useI18n()

const { required } = useValidator()

const { tableRegister, tableState, tableMethods } = useTable({
  immediate: false,
  fetchDataApi: async () => {
    const res = await getSecretsApi({
      page: currentPage.value,
      size: pageSize.value,
      ...unref(searchParams)
    })
    return {
      list: res.data || [],
      total: res.total
    }
  }
})

const userStore = useUserStoreWithOut()
const currentObjectId = ref('')

const { dataList, loading, total, currentPage, pageSize } = tableState
const { getList } = tableMethods

const tableColumns = reactive<TableColumn[]>([
  {
    field: 'object',
    label: t('managedObject.secretObj'),
    width: 140
  },
  {
    field: 'username',
    label: t('userDemo.account'),
    width: 140
  },
  {
    field: 'password',
    label: t('userDemo.password'),
    width: 280,
    slots: {
      default: (data: any) => {
        return (
          <PasswordDisplay
            value={data.row.password}
            showCopy={true}
            showToggle={true}
            maxLength={20}
          />
        )
      }
    }
  },
  {
    field: 'url',
    label: t('managedObject.url')
  },
  {
    field: 'created_at',
    label: t('userDemo.createTime'),
    width: 170
  },
  {
    field: 'updated_at',
    label: t('userDemo.updateTime'),
    width: 170
  }
])

const searchFormRules: FormRules = {
  managed_object_id: [required()]
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
                <ElOption
                  key={item.id}
                  label={item.system_id + ' (' + item.system_type + ') | ' + item.worker_name}
                  value={item.id}
                >
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
      }
    }
  },
  {
    field: 'q',
    //label: t('role.roleName'),
    component: 'Input'
  }
])

const searchParams = ref({})

const setSearchParams = (data: any) => {
  searchParams.value = data
  currentObjectId.value = data.managed_object_id
  getList()
}

const managedObjects = ref<ManagedObjectItem[]>([])

const fetchManagedObjects = () => {
  if (userStore.getWorkspace) {
    getManagedObjectsApi('secret').then((res) => {
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
    <Search
      :schema="searchSchema"
      :rules="searchFormRules"
      :showReset="false"
      @search="setSearchParams"
    />
    <Table
      v-model:pageSize="pageSize"
      v-model:currentPage="currentPage"
      :columns="tableColumns"
      node-key="change_set_id"
      row-key="change_set_id"
      :data="dataList"
      :loading="loading"
      :pagination="{
        total
      }"
      @register="tableRegister"
    />
  </ContentWrap>
</template>
