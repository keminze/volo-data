import { apiRequest } from "./request";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email?: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

export async function login(data: LoginRequest): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: data,
  });
}

export async function register(data: RegisterRequest): Promise<UserInfo> {
  return apiRequest<UserInfo>("/auth/register", {
    method: "POST",
    body: data,
  });
}

export async function getCurrentUser(): Promise<UserInfo> {
  return apiRequest<UserInfo>("/auth/me", {
    method: "GET",
  });
}