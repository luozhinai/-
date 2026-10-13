import apiClient from './index';

export type AuthStatusResponse = {
  authEnabled: boolean;
  loggedIn: boolean;
  passwordSet?: boolean;
  passwordChangeable?: boolean;
  setupState: 'enabled' | 'password_retained' | 'no_password';
  accountMode?: boolean;
  adminExists?: boolean;
  legacyPasswordRequired?: boolean;
  user?: { id: string; username: string; role: 'admin' | 'user' } | null;
};

export const authApi = {
  async getStatus(): Promise<AuthStatusResponse> {
    const { data } = await apiClient.get<AuthStatusResponse>('/api/v1/auth/status');
    return data;
  },

  async updateSettings(
    authEnabled: boolean,
    password?: string,
    passwordConfirm?: string,
    currentPassword?: string
  ): Promise<AuthStatusResponse> {
    const body: {
      authEnabled: boolean;
      password?: string;
      passwordConfirm?: string;
      currentPassword?: string;
    } = { authEnabled };
    if (password !== undefined) {
      body.password = password;
    }
    if (passwordConfirm !== undefined) {
      body.passwordConfirm = passwordConfirm;
    }
    if (currentPassword !== undefined) {
      body.currentPassword = currentPassword;
    }
    const { data } = await apiClient.post<AuthStatusResponse>('/api/v1/auth/settings', body);
    return data;
  },

  async login(password: string, passwordConfirm?: string, username?: string): Promise<void> {
    const body: { password: string; passwordConfirm?: string; username?: string } = { password };
    if (username !== undefined) body.username = username;
    if (passwordConfirm !== undefined) {
      body.passwordConfirm = passwordConfirm;
    }
    await apiClient.post('/api/v1/auth/login', body);
  },

  async register(username: string, password: string, passwordConfirm: string, legacyPassword?: string): Promise<void> {
    await apiClient.post('/api/v1/auth/register', { username, password, passwordConfirm, legacyPassword });
  },

  async changePassword(
    currentPassword: string,
    newPassword: string,
    newPasswordConfirm: string
  ): Promise<void> {
    await apiClient.post('/api/v1/auth/change-password', {
      currentPassword,
      newPassword,
      newPasswordConfirm,
    });
  },

  async logout(): Promise<void> {
    await apiClient.post('/api/v1/auth/logout');
  },
};
