import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import AuthForm from '../AuthForm';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('AuthForm Component', () => {
  const mockOnSubmit = jest.fn();
  const mockOnRememberMeChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Register Form', () => {
    it('renders all registration fields', () => {
      render(
        <AuthForm
          type="register"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
        />
      );

      expect(screen.getByLabelText(/姓名/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/邮箱地址/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/密码/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/确认密码/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /注册/i })).toBeInTheDocument();
    });

    it('validates form fields on blur', async () => {
      const user = userEvent.setup();
      render(
        <AuthForm
          type="register"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
        />
      );

      const nameInput = screen.getByLabelText(/姓名/i);
      const emailInput = screen.getByLabelText(/邮箱地址/i);
      const passwordInput = screen.getByLabelText(/密码/i);

      // Test empty field validation
      await user.click(nameInput);
      await user.tab(); // Blur the field
      await waitFor(() => {
        expect(screen.getByText(/姓名不能为空/i)).toBeInTheDocument();
      });

      // Test invalid email
      await user.type(emailInput, 'invalid-email');
      await user.tab(); // Blur the field
      await waitFor(() => {
        expect(screen.getByText(/请输入有效的邮箱地址/i)).toBeInTheDocument();
      });

      // Test short password
      await user.type(passwordInput, '123');
      await user.tab(); // Blur the field
      await waitFor(() => {
        expect(screen.getByText(/密码至少需要8个字符/i)).toBeInTheDocument();
      });
    });

    it('shows password strength indicator', async () => {
      const user = userEvent.setup();
      render(
        <AuthForm
          type="register"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
        />
      );

      const passwordInput = screen.getByLabelText(/密码/i);
      await user.type(passwordInput, 'weakpass');

      // Password strength indicator should be visible
      expect(screen.getByText(/密码强度/i)).toBeInTheDocument();
    });

    it('toggles password visibility', async () => {
      const user = userEvent.setup();
      render(
        <AuthForm
          type="register"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
        />
      );

      const passwordInput = screen.getByLabelText(/密码/i) as HTMLInputElement;
      const toggleButton = screen.getByRole('button', { name: /toggle password visibility/i });

      expect(passwordInput.type).toBe('password');

      await user.click(toggleButton);
      expect(passwordInput.type).toBe('text');

      await user.click(toggleButton);
      expect(passwordInput.type).toBe('password');
    });
  });

  describe('Login Form', () => {
    it('renders login fields', () => {
      render(
        <AuthForm
          type="login"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
          rememberMe={false}
          onRememberMeChange={mockOnRememberMeChange}
        />
      );

      expect(screen.queryByLabelText(/姓名/i)).not.toBeInTheDocument();
      expect(screen.getByLabelText(/邮箱地址/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/密码/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/记住登录状态/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /登录/i })).toBeInTheDocument();
    });

    it('calls onRememberMeChange when checkbox is toggled', async () => {
      const user = userEvent.setup();
      render(
        <AuthForm
          type="login"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
          rememberMe={false}
          onRememberMeChange={mockOnRememberMeChange}
        />
      );

      const rememberCheckbox = screen.getByLabelText(/记住登录状态/i);
      await user.click(rememberCheckbox);

      expect(mockOnRememberMeChange).toHaveBeenCalledWith(true);
    });

    it('loads remembered email on mount', () => {
      localStorageMock.getItem.mockReturnValue('remembered@example.com');

      render(
        <AuthForm
          type="login"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
          rememberMe={false}
          onRememberMeChange={mockOnRememberMeChange}
        />
      );

      expect(screen.getByDisplayValue('remembered@example.com')).toBeInTheDocument();
      expect(localStorageMock.getItem).toHaveBeenCalledWith('remember_email');
    });
  });

  describe('Form Submission', () => {
    it('submits form with valid data', async () => {
      const user = userEvent.setup();
      render(
        <AuthForm
          type="register"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
        />
      );

      await user.type(screen.getByLabelText(/姓名/i), 'Test User');
      await user.type(screen.getByLabelText(/邮箱地址/i), 'test@example.com');
      await user.type(screen.getByLabelText(/密码/i), 'testpassword123');
      await user.type(screen.getByLabelText(/确认密码/i), 'testpassword123');

      await user.click(screen.getByRole('button', { name: /注册/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'testpassword123',
          confirmPassword: 'testpassword123',
          fullName: 'Test User'
        });
      });
    });

    it('does not submit form with invalid data', async () => {
      const user = userEvent.setup();
      render(
        <AuthForm
          type="register"
          onSubmit={mockOnSubmit}
          loading={false}
          error=""
        />
      );

      // Try to submit without filling required fields
      await user.click(screen.getByRole('button', { name: /注册/i }));

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Error Display', () => {
    it('displays error message when provided', () => {
      render(
        <AuthForm
          type="login"
          onSubmit={mockOnSubmit}
          loading={false}
          error="Invalid credentials"
        />
      );

      expect(screen.getByText(/登录失败/i)).toBeInTheDocument();
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('disables form and shows loading when loading', () => {
      render(
        <AuthForm
          type="login"
          onSubmit={mockOnSubmit}
          loading={true}
          error=""
        />
      );

      expect(screen.getByRole('button', { name: /登录中/i })).toBeDisabled();
      expect(screen.getByText(/登录中/i)).toBeInTheDocument();
    });
  });
});