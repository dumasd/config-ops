<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/store/modules/app'
import { usePermissionStore } from '@/store/modules/permission'
import { useRouter } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { oidcCallbackApi, getUserMenusApi } from '@/api/login'

const appStore = useAppStore()
const userStore = useUserStore()
const permissionStore = usePermissionStore()
const redirect = ref<string>('')
const { currentRoute, addRoute, push } = useRouter()

oidcCallbackApi(currentRoute.value.query).then((res) => {
  console.log('111111111')
  userStore.setUserInfo(res.data)
  // 是否使用动态路由
  if (appStore.getDynamicRouter) {
    getRole()
  } else {
    permissionStore.generateRoutes('static').catch(() => {})
    permissionStore.getAddRouters.forEach((route) => {
      addRoute(route as RouteRecordRaw) // 动态添加可访问路由表
    })
    permissionStore.setIsAddRouters(true)
    push({ path: redirect.value || permissionStore.addRouters[0].path })
  }
})

// 获取角色信息
const getRole = async () => {
  const res = await getUserMenusApi()
  if (res) {
    const routers = res.data || []
    userStore.setRoleRouters(routers)
    /*appStore.getDynamicRouter && appStore.getServerDynamicRouter
      ? await permissionStore.generateRoutes('server', routers).catch(() => {})
      : await permissionStore.generateRoutes('frontEnd', routers).catch(() => {})*/
    await permissionStore.generateRoutes('frontEnd', routers).catch(() => {})
    permissionStore.getAddRouters.forEach((route) => {
      addRoute(route as RouteRecordRaw) // 动态添加可访问路由表
    })
    permissionStore.setIsAddRouters(true)
    push({ path: redirect.value || permissionStore.addRouters[0].path })
  }
}
</script>

<template>
  <div></div>
</template>
