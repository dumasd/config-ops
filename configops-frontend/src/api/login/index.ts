import request from '@/axios'
import type { UserType, Workspace } from './types'

interface RoleParams {
  roleName: string
}

interface OIDCInfo {
  enabled: boolean
  auto_login: boolean
  login_txt: boolean
  sso_url: string
}

export const loginApi = (data: UserType): Promise<IResponse<UserType>> => {
  return request.post({ url: '/mock/user/login', data })
}

export const loginOutApi = (): Promise<IResponse> => {
  return request.delete({ url: '/api/user/logout' })
}

export const getUserListApi = ({ params }: AxiosConfig) => {
  return request.get<{
    code: string
    data: {
      list: UserType[]
      total: number
    }
  }>({ url: '/mock/user/list', params })
}

export const oidcInfoApi = (): Promise<IResponse<OIDCInfo>> => {
  return request.get({ url: '/api/oidc/info' })
}

export const oidcLoginApi = () => {
  return request.get({ url: '/api/oidc/login' })
}

export const oidcCallbackApi = (params) => {
  return request.get({ url: '/api/oidc/callback', params: params })
}

export const getAdminRoleApi = (
  params: RoleParams
): Promise<IResponse<AppCustomRouteRecordRaw[]>> => {
  return request.get({ url: '/mock/role/list', params })
}

export const getUserMenusApi = (): Promise<IResponse<string[]>> => {
  return request.get({ url: '/api/user/menus' })
}

export const getUserWorkspacesApi = (): Promise<IResponse<Workspace[]>> => {
  return request.get({ url: '/api/user/workspaces' })
}
