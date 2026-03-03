export type UserRole = "admin" | "editor" | "viewer";

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_api_enabled: boolean;
  is_active: boolean;
  date_joined: string;
}
