import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LoginPage from '../LoginPage';

const { navigate, useSearchParamsMock, useAuthMock } = vi.hoisted(() => ({
  navigate: vi.fn(),
  useSearchParamsMock: vi.fn(),
  useAuthMock: vi.fn(),
}));

vi.mock('../../hooks', () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigate,
    useSearchParams: () => useSearchParamsMock(),
  };
});

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.documentElement.className = 'light';
    useSearchParamsMock.mockReturnValue([new URLSearchParams('redirect=%2Fsettings')]);
  });

  it('blocks first-time setup when confirmation does not match', async () => {
    const login = vi.fn();
    useAuthMock.mockReturnValue({
      login,
      passwordSet: false,
      setupState: 'no_password',
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText('管理员密码'), { target: { value: 'passwd6' } });
    fireEvent.change(screen.getByLabelText('确认密码'), { target: { value: 'passwd7' } });
    fireEvent.click(screen.getByRole('button', { name: '完成设置并登录' }));

    expect(await screen.findByText('两次输入的密码不一致')).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
    expect(screen.getByLabelText('管理员密码')).toHaveAttribute('data-appearance', 'login');
    expect(screen.getByLabelText('确认密码')).toHaveAttribute('data-appearance', 'login');
  });

  it('navigates to redirect after a successful login', async () => {
    useAuthMock.mockReturnValue({
      login: vi.fn().mockResolvedValue({ success: true }),
      passwordSet: true,
      setupState: 'enabled',
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText('登录密码'), { target: { value: 'passwd6' } });
    fireEvent.click(screen.getByRole('button', { name: '授权进入工作台' }));

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/settings', { replace: true }));
    expect(screen.getByLabelText('登录密码')).toHaveAttribute('data-appearance', 'login');
  });

  it('does not override login theme tokens inline so light mode can take effect', () => {
    useAuthMock.mockReturnValue({
      login: vi.fn(),
      passwordSet: true,
      setupState: 'enabled',
    });

    const { container } = render(<LoginPage />);
    const pageRoot = container.firstElementChild as HTMLElement | null;

    expect(pageRoot).not.toBeNull();
    expect(pageRoot?.getAttribute('style') ?? '').not.toContain('--login-bg-main');
  });

  it('uses the existing login design for first administrator registration', async () => {
    const register = vi.fn().mockResolvedValue({ success: true });
    useAuthMock.mockReturnValue({
      accountMode: true,
      adminExists: false,
      legacyPasswordRequired: true,
      register,
    });

    render(<LoginPage />);

    expect(screen.getByText('DAILY')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '注册' })).toHaveAttribute('aria-selected', 'true');
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'owner' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'new-secret-123' } });
    fireEvent.change(screen.getByLabelText('确认密码'), { target: { value: 'new-secret-123' } });
    fireEvent.change(screen.getByLabelText('原管理员密码'), { target: { value: 'old-secret' } });
    fireEvent.click(screen.getByRole('button', { name: '创建管理员账户' }));

    await waitFor(() => expect(register).toHaveBeenCalledWith('owner', 'new-secret-123', 'new-secret-123', 'old-secret'));
    expect(navigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('registers an ordinary account after the administrator already exists', async () => {
    const register = vi.fn().mockResolvedValue({ success: true });
    useAuthMock.mockReturnValue({
      accountMode: true,
      adminExists: true,
      legacyPasswordRequired: false,
      register,
    });

    render(<LoginPage />);

    fireEvent.click(screen.getByRole('tab', { name: '注册' }));
    expect(screen.getByRole('button', { name: '创建普通账户' })).toBeInTheDocument();
    expect(screen.queryByLabelText('原管理员密码')).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText('再次确认密码')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'customer' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'new-secret-123' } });
    fireEvent.change(screen.getByLabelText('确认密码'), { target: { value: 'new-secret-123' } });
    fireEvent.click(screen.getByRole('button', { name: '创建普通账户' }));

    await waitFor(() => expect(register).toHaveBeenCalledWith('customer', 'new-secret-123', 'new-secret-123', undefined));
    expect(navigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('uses the same design for account login and returns to the requested page', async () => {
    const login = vi.fn().mockResolvedValue({ success: true });
    useAuthMock.mockReturnValue({
      accountMode: true,
      adminExists: true,
      login,
    });

    render(<LoginPage />);

    expect(screen.getByText('DAILY')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '登录' })).toHaveAttribute('aria-selected', 'true');
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'owner' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'new-secret-123' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));

    await waitFor(() => expect(login).toHaveBeenCalledWith('new-secret-123', undefined, 'owner'));
    expect(navigate).toHaveBeenCalledWith('/settings', { replace: true });
  });
});
