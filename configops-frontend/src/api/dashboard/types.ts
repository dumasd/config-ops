export interface ManagedObjectItem {
  id: string
  system_id: string
  worker_id: string
  worker_name: string
  system_type: string
  url: string
}

export type ChangelogItem = {
  id: string
  system_id: string
  system_type: string
  author: string
  filename: string
  checksum: string
  exectype: string
  comment: string
  labels: string
}
