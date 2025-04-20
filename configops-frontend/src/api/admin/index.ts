import request from '@/axios'
import { WorkspaceItem, GroupPermissionsItem, ManagedObjectItem, GroupItem } from './types'

export const getGroupsApi = (searchParams): Promise<IResponse<GroupItem[]>> => {
  return request.get({ url: '/api/admin/group/v1', params: searchParams })
}

export const getGroupMenusApi = (group_id): Promise<IResponse<string[]>> => {
  return request.get({ url: '/api/admin/group/menus/v1', params: { id: group_id } })
}

export const createGroupApi = (item): Promise<IResponse<string[]>> => {
  return request.post({ url: '/api/admin/group/v1', data: item })
}

export const editGroupApi = (item): Promise<IResponse<string[]>> => {
  return request.put({ url: '/api/admin/group/v1', data: item })
}

export const getWorkspacesApi = (searchParams): Promise<IResponse<WorkspaceItem[]>> => {
  return request.get({ url: '/api/admin/workspace/v1', params: searchParams })
}

export const createWorkspacesApi = (item) => {
  return request.post({ url: '/api/admin/workspace/v1', data: item })
}

export const editWorkspacesApi = (item) => {
  return request.put({ url: '/api/admin/workspace/v1', data: item })
}

export const deleteWorkspacesApi = (id) => {
  return request.delete({ url: '/api/admin/workspace/v1', params: { id: id } })
}

export const getWorkspacePermissionApi = (id): Promise<IResponse<GroupPermissionsItem[]>> => {
  return request.get({ url: '/api/admin/workspace/permission/v1', params: { id: id } })
}

export const editWorkspacePermissionApi = (id, data: GroupPermissionsItem[]) => {
  return request.put({ url: '/api/admin/workspace/permission/v1', params: { id: id }, data: data })
}

export const getWorkerApi = (searchParams) => {
  return request.get({ url: '/api/admin/worker/v1', params: searchParams })
}

export const createWorkerApi = (item) => {
  return request.post({ url: '/api/admin/worker/v1', data: item })
}

export const editWorkerApi = (item) => {
  return request.put({ url: '/api/admin/worker/v1', data: item })
}

export const delteWorkerApi = (id) => {
  return request.delete({ url: '/api/admin/worker/v1', params: { id: id } })
}

export const getManagedObjectApi = (searchParams): Promise<IResponse<ManagedObjectItem[]>> => {
  return request.get({ url: '/api/admin/managed_object/v1', params: searchParams })
}

export const getManagedObjectPermissionApi = (id): Promise<IResponse<GroupPermissionsItem[]>> => {
  return request.get({ url: '/api/admin/managed_object/permission/v1', params: { id: id } })
}

export const editManagedObjectPermissionApi = (id, data: GroupPermissionsItem[]) => {
  return request.put({
    url: '/api/admin/managed_object/permission/v1',
    params: { id: id },
    data: data
  })
}
