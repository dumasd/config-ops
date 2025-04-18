export interface UserLoginType {
  username: string
  password: string
}

export interface UserType {
  username: string
  password: string
  role: string
  roleId: string
}

export interface UserInfo {
  id: string
  name: string
}

export interface Workspace {
  id: string
  name: string
  description: string
}
