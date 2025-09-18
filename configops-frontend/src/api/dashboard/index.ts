import request from '@/axios'
import type { ChangelogItem, ManagedObjectItem, ManagedObjectSecretItem } from './types'

export const getManagedObjectsApi = (f: string): Promise<IResponse<ManagedObjectItem[]>> => {
  return request.get({ url: '/api/dashboard/managed_objects/v1', params: { f: f } })
}

export const getChangelogsApi = (searchParams): Promise<IResponse<ChangelogItem[]>> => {
  return request.get({ url: '/api/dashboard/changelogs/v1', params: searchParams })
}

export const deleteChangelogsApi = (
  managed_object_id,
  data: ChangelogItem[]
): Promise<IResponse<ChangelogItem[]>> => {
  return request.delete({
    url: '/api/dashboard/changelogs/v1',
    params: { managed_object_id: managed_object_id },
    data: data
  })
}

export const updateChangelogsApi = (
  managed_object_id,
  data: any[]
): Promise<IResponse<any>> => {
  return request.put({
    url: '/api/dashboard/changelogs/v1',
    params: { managed_object_id: managed_object_id },
    data: data
  })
}

export const getChangesetApi = (searchParams): Promise<IResponse<ChangelogItem[]>> => {
  return request.get({ url: '/api/dashboard/changeset/v1', params: searchParams })
}

export const getSecretsApi = (searchParams): Promise<IResponse<ManagedObjectSecretItem[]>> => {
  return request.get({ url: '/api/dashboard/secrets/v1', params: searchParams })
}
