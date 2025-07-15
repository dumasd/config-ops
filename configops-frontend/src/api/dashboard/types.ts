export interface ManagedObjectItem {
  id: string
  system_id: string
  worker_id: string
  worker_name: string
  system_type: string
  url: string
}

export type ChangelogItem = {
  change_set_id: string
  system_id: string
  system_type: string
  author: string
  filename: string
  checksum: string
  exectype: string
  comment: string
  labels: string
}

export interface ManagedObjectSecretItem {
  system_id: string
  system_type: string
  object: string
  username: string
  password: string
  url: string
  created_at: string
  updated_at: string
}
