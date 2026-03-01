/** Standard DRF paginated response */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** JWT auth tokens */
export interface AuthTokens {
  access: string;
  refresh: string;
}

/** Login credentials */
export interface LoginCredentials {
  username: string;
  password: string;
}

/** Registration data */
export interface RegisterData {
  username: string;
  email: string;
  password1: string;
  password2: string;
}
