export interface WorkspaceItem {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
}

export interface GroupPermissionsItem {
  group_id: string
  permissions: string[]
}

export interface ManagedObjectItem {
  id: string
  key: string
  worker_id: string
  worker_name: string
  system_type: string
  url: string
}

export interface GroupItem {
  id: string
  name: string
  description: string
  menus?: Array<string>
}
