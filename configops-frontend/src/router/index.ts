import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import type { App } from 'vue'
import { Layout, getParentLayout } from '@/utils/routerHelper'
import { useI18n } from '@/hooks/web/useI18n'
import { NO_RESET_WHITE_LIST } from '@/constants'

const { t } = useI18n()

export const constantRouterMap: AppRouteRecordRaw[] = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard/changelog',
    name: 'Root',
    meta: {
      hidden: true
    }
  },
  {
    path: '/redirect',
    component: Layout,
    name: 'RedirectWrap',
    children: [
      {
        path: '/redirect/:path(.*)',
        name: 'Redirect',
        component: () => import('@/views/Redirect/Redirect.vue'),
        meta: {}
      }
    ],
    meta: {
      hidden: true,
      noTagsView: true
    }
  },
  {
    path: '/login',
    component: () => import('@/views/Login/Login.vue'),
    name: 'Login',
    meta: {
      hidden: true,
      title: t('router.login'),
      noTagsView: true
    }
  },
  {
    path: '/oidc/callback',
    component: () => import('@/views/Login/oidc/Callback.vue'),
    name: 'OidcCallback',
    meta: {
      title: t('router.personalCenter'),
      hidden: true,
      noTagsView: true
    }
  },
  {
    path: '/personal',
    component: Layout,
    redirect: '/personal/personal-center',
    name: 'Personal',
    meta: {
      title: t('router.personal'),
      hidden: true,
      canTo: true
    },
    children: [
      {
        path: 'personal-center',
        component: () => import('@/views/Personal/PersonalCenter/PersonalCenter.vue'),
        name: 'PersonalCenter',
        meta: {
          title: t('router.personalCenter'),
          hidden: true,
          canTo: true
        }
      }
    ]
  },
  {
    path: '/404',
    component: () => import('@/views/Error/404.vue'),
    name: 'NoFind',
    meta: {
      hidden: true,
      title: '404',
      noTagsView: true
    }
  }
]

export const asyncRouterMap: AppRouteRecordRaw[] = [
  {
    path: '/dashboard',
    component: Layout,
    redirect: '/dashboard/changelog',
    name: 'Dashboard',
    meta: {
      title: t('router.dashboard'),
      icon: 'vi-ant-design:dashboard-filled',
      alwaysShow: true
    },
    fullPath: '/dashboard',
    children: [
      /*{
        path: 'analysis',
        component: () => import('@/views/Dashboard/Analysis.vue'),
        name: 'Analysis',
        fullPath: '/dashboard/analysis',
        meta: {
          title: t('router.analysis'),
          noCache: true,
          affix: true
        }
      },
      {
        path: 'workplace',
        component: () => import('@/views/Dashboard/Workplace.vue'),
        name: 'Workplace',
        fullPath: '/dashboard/workplace',
        meta: {
          title: t('router.workplace'),
          noCache: true
        }
      },*/
      {
        path: 'changelog',
        component: () => import('@/views/Dashboard/Changelog/Changelog.vue'),
        name: 'Changelog',
        fullPath: '/dashboard/changelog',
        meta: {
          title: t('router.workplace'),
          noCache: true
        }
      },
      {
        path: 'object',
        component: () => import('@/views/Dashboard/ManagedObject/ManagedObject.vue'),
        name: 'Object',
        fullPath: '/dashboard/object',
        meta: {
          title: t('router.objectManagement')
        }
      },
      {
        path: 'worker',
        component: () => import('@/views/Dashboard/Worker/Worker.vue'),
        name: 'Worker',
        fullPath: '/dashboard/worker',
        meta: {
          title: t('router.workerManagement')
        }
      }
    ]
  },
  {
    path: '/authorization',
    component: Layout,
    redirect: '/authorization/user',
    name: 'Authorization',
    fullPath: '/authorization',
    meta: {
      title: t('router.systemManagement'),
      icon: 'vi-eos-icons:role-binding',
      alwaysShow: true
    },
    children: [
      {
        path: 'user',
        component: () => import('@/views/Authorization/User/User.vue'),
        name: 'User',
        fullPath: '/authorization/user',
        meta: {
          title: t('router.user')
        }
      },
      {
        path: 'role',
        component: () => import('@/views/Authorization/Role/Role.vue'),
        name: 'Role',
        fullPath: '/authorization/role',
        meta: {
          title: t('router.role')
        }
      },
      {
        path: 'workspace',
        component: () => import('@/views/Authorization/Workspace/Workspace.vue'),
        name: 'Workspace',
        fullPath: '/authorization/workspace',
        meta: {
          title: t('router.workspaceManagement')
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.VITE_BASE_PATH),
  strict: true,
  routes: constantRouterMap as RouteRecordRaw[],
  scrollBehavior: () => ({ left: 0, top: 0 })
})

export const resetRouter = (): void => {
  router.getRoutes().forEach((route) => {
    const { name } = route
    if (name && !NO_RESET_WHITE_LIST.includes(name as string)) {
      router.hasRoute(name) && router.removeRoute(name)
    }
  })
}

export const setupRouter = (app: App<Element>) => {
  app.use(router)
}

export default router
