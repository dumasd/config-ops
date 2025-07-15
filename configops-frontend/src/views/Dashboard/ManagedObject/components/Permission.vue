<script setup lang="ts">
import { ContentWrap } from '@/components/ContentWrap'
import { getManagedObjectPermissionApi } from '@/api/admin'
import { PropType, ref, unref } from 'vue'
import { ManagedObjectItem, GroupPermissionsItem } from '@/api/admin/types'
import { ElTree, ElDivider, ElCheckboxGroup, ElCheckbox } from 'element-plus'

const treeEl = ref<typeof ElTree>()

const props = defineProps({
  currentRow: {
    type: Object as PropType<ManagedObjectItem>,
    default: () => undefined
  }
})

const groupPermissions = ref<GroupPermissionsItem[]>([])

const permissionTemplate = ref([
  {
    module: 'MANAGED_OBJECT_CHANGELOG_MANAGE',
    checkList: [''],
    actions: ['READ', 'CREATE', 'EDIT', 'DELETE']
  },
  {
    module: 'MANAGED_OBJECT_SECRET_MANAGE',
    checkList: [''],
    actions: ['READ']
  }
])

const handleGroupClick = (data: GroupPermissionsItem) => {
  for (const _template of permissionTemplate.value) {
    _template.checkList = []
  }

  for (const _moduleActions of data.permissions) {
    const _module = _moduleActions.split(':')[0]
    const _actions = _moduleActions.split(':')[1].split('+')
    const templates = permissionTemplate.value
    const idx = templates.findIndex((item) => item.module === _module)
    if (idx >= 0) {
      if (_actions.indexOf('ALL') >= 0) {
        templates[idx].checkList = templates[idx].actions
      } else {
        templates[idx].checkList = _actions
      }
    }
  }
}

const handleActionChange = (val) => {
  const group = unref(treeEl)?.getCurrentNode()
  if (group) {
    const groupPermission = groupPermissions.value.find((item) => item.group_id === group.group_id)
    if (groupPermission) {
      const permissions: string[] = []
      for (const item of permissionTemplate.value) {
        if (item.checkList.length > 0) {
          permissions.push(item.module + ':' + item.checkList.join('+'))
        }
      }
      groupPermission.permissions = permissions
    }
  }
}

const submit = () => {
  return {
    id: props.currentRow?.id,
    groupPermissions: groupPermissions.value
  }
}

defineExpose({
  submit
})

getManagedObjectPermissionApi(props.currentRow?.id).then((res) => {
  groupPermissions.value = res.data
})
</script>

<template>
  <div class="flex w-100% h-100%">
    <ContentWrap class="w-300px">
      <ElTree
        ref="treeEl"
        node-key="group_id"
        :data="groupPermissions"
        default-expand-all
        :expand-on-click-node="false"
        highlight-current
        :props="{
          label: 'group_name',
          children: 'children'
        }"
        @node-click="handleGroupClick"
      >
        <template #default="{ data }">
          <div :title="data.group_name" class="whitespace-nowrap overflow-ellipsis overflow-hidden">
            {{ data.group_name }}
          </div>
        </template>
      </ElTree>
    </ContentWrap>
    <ContentWrap class="flex-[3] ml-20px">
      <div v-for="template in permissionTemplate" :key="template.module">
        <ElDivider content-position="left">{{ template.module }}</ElDivider>
        <ElCheckboxGroup v-model="template.checkList" @change="handleActionChange">
          <ElCheckbox
            v-for="child in template.actions"
            :key="child"
            :label="child"
            :value="child"
            :checked="template.checkList.indexOf(child) >= 0"
            >{{ child }}
          </ElCheckbox>
        </ElCheckboxGroup>
      </div>
    </ContentWrap>
  </div>
</template>
