<script setup lang="tsx">
import { Form, FormSchema } from '@/components/Form'
import { useForm } from '@/hooks/web/useForm'
import { PropType, reactive, watch, ref, unref, nextTick } from 'vue'
import { useValidator } from '@/hooks/web/useValidator'
import { useI18n } from '@/hooks/web/useI18n'
import { ElTree, ElCheckboxGroup, ElCheckbox } from 'element-plus'
import { cloneDeep } from 'lodash-es'
import { getGroupMenusApi } from '@/api/admin'
import { GroupItem } from '@/api/admin/types'
import { asyncRouterMap } from '@/router'

const { t } = useI18n()

const { required } = useValidator()

const props = defineProps({
  currentRow: {
    type: Object as PropType<GroupItem>,
    default: () => null
  }
})

const treeRef = ref<typeof ElTree>()

const formSchema = ref<FormSchema[]>([
  {
    field: 'name',
    label: t('role.roleName'),
    component: 'Input'
  },
  {
    field: 'menu',
    label: t('role.menu'),
    colProps: {
      span: 24
    },
    formItemProps: {
      slots: {
        default: () => {
          return (
            <>
              <div class="flex w-full">
                <div class="flex-1">
                  <ElTree
                    ref={treeRef}
                    show-checkbox
                    node-key="fullPath"
                    highlight-current
                    check-strictly
                    expand-on-click-node={false}
                    data={treeData.value}
                    onNode-click={nodeClick}
                  >
                    {{
                      default: (data) => {
                        return <span>{data.data.name}</span>
                      }
                    }}
                  </ElTree>
                </div>
                <div class="flex-1">
                  {unref(currentTreeData) && unref(currentTreeData)?.permissionList ? (
                    <ElCheckboxGroup v-model={unref(currentTreeData).meta.permission}>
                      {unref(currentTreeData)?.permissionList.map((v: any) => {
                        return <ElCheckbox label={v.value}>{v.label}</ElCheckbox>
                      })}
                    </ElCheckboxGroup>
                  ) : null}
                </div>
              </div>
            </>
          )
        }
      }
    }
  },
  {
    field: 'id',
    label: t('common.id'),
    component: 'Input',
    hidden: true
  }
])

const currentTreeData = ref()
const nodeClick = (treeData: any) => {
  currentTreeData.value = treeData
}

const rules = reactive({
  name: [required()]
})

const { formRegister, formMethods } = useForm()
const { setValues, getFormData, getElFormExpose } = formMethods

const treeData = ref<AppRouteRecordRaw[]>([])
const getMenuList = async () => {
  treeData.value = cloneDeep(asyncRouterMap)
  if (!props.currentRow) return
  await nextTick()
  const menus: string[] = (await getGroupMenusApi(props.currentRow.id)).data
  unref(treeRef)?.setCheckedKeys(menus, false)
}

getMenuList()

const submit = async () => {
  const elForm = await getElFormExpose()
  const valid = await elForm?.validate().catch((err) => {
    console.log(err)
  })
  if (valid) {
    const formData = await getFormData()
    const checkedKeys = unref(treeRef)?.getCheckedKeys() || []
    formData.menus = checkedKeys
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
