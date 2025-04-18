<script setup lang="ts">
import { ElDropdown, ElDropdownItem, ElDropdownMenu } from 'element-plus'
import { ref, watch } from 'vue'
import { useUserStoreWithOut } from '@/store/modules/user'
import { getUserWorkspacesApi } from '@/api/login'
import { Workspace } from '@/api/login/types'
import { propTypes } from '@/utils/propTypes'
import { useDesign } from '@/hooks/web/useDesign'

const { getPrefixCls } = useDesign()

const prefixCls = getPrefixCls('locale-dropdown')

defineProps({
  color: propTypes.string.def('')
})
const userStore = useUserStoreWithOut()
const workspaces = ref<Workspace[]>([])
const selectedWorkspace = ref<Workspace>({ id: '', name: 'None', description: '' })

const selectedWorkspaceChange = (workspace: Workspace) => {
  selectedWorkspace.value = workspace
  userStore.setWorkspace(workspace.id)
}

const fetchUserWorkspaces = () => {
  if (userStore.userInfo) {
    getUserWorkspacesApi().then((res) => {
      workspaces.value = res.data
      for (const item of res.data) {
        if (item.id == userStore.getWorkspace) {
          selectedWorkspaceChange(item)
          return
        }
      }
      if (res.data.length > 0) {
        selectedWorkspaceChange(res.data[0])
      }
    })
  }
}

watch(
  () => userStore.userInfo,
  (newVal, oldVal) => {
    fetchUserWorkspaces()
  }
)

fetchUserWorkspaces()
</script>

<template>
  <ElDropdown :class="prefixCls" @command="selectedWorkspaceChange">
    <span class="<lg:hidden text-14px pl-[5px] text-[var(--top-header-text-color)]">
      {{ selectedWorkspace.name }}
      <Icon
        :size="10"
        icon="vi-ant-design:caret-down-outlined"
        class="cursor-pointer !p-0"
        :class="$attrs.class"
        :color="color"
      />
    </span>
    <template #dropdown>
      <ElDropdownMenu>
        <ElDropdownItem v-for="workspace in workspaces" :key="workspace.id" :command="workspace">{{
          workspace.name
        }}</ElDropdownItem>
      </ElDropdownMenu>
    </template>
  </ElDropdown>
</template>
