/**
 * APIKeysManager Component Tests
 * Week 4 Day 27: System Integration Testing and Documentation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { jest } from '@testing-library/jest-dom';
import APIKeysManager from '../APIKeysManager';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    })
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock fetch
global.fetch = jest.fn();

describe('APIKeysManager Component', () => {
  const mockDeveloper = {
    id: 'developer-1',
    email: 'test@example.com',
    full_name: 'Test Developer',
    email_verified: true,
    created_at: '2024-01-01T00:00:00Z'
  };

  const mockAPIKeys = [
    {
      id: 'key-1',
      name: 'Test Key 1',
      key_prefix: 'test_key_123456',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      last_used: '2024-01-01T12:00:00Z'
    },
    {
      id: 'key-2',
      name: 'Test Key 2',
      key_prefix: 'test_key_789012',
      is_active: false,
      created_at: '2024-01-02T00:00:00Z',
      last_used: null
    }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();

    // Mock fetch responses
    (fetch as jest.Mock).mockImplementation((url) => {
      if (url.includes('/api/v1/developer/auth/me')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: mockDeveloper
          })
        });
      }
      if (url.includes('/api/v1/developer/keys')) {
        if (url.includes('/keys/') && (url.includes('POST') || url.includes('DELETE'))) {
          // Create/delete operations
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              success: true,
              data: { message: 'API key operation successful' }
            })
          });
        } else {
          // List operation
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              success: true,
              data: mockAPIKeys
            })
          });
        }
      }
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: "Not found" })
      });
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders API keys manager correctly', () => {
    render(<APIKeysManager />);

    expect(screen.getByText('API 密钥管理')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /创建新密钥/i })).toBeInTheDocument();
  });

  it('loads and displays API keys', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Key 1')).toBeInTheDocument();
      expect(screen.getByText('test_key_123456')).toBeInTheDocument();
      expect(screen.getByText('Test Key 2')).toBeInTheDocument();
      expect(screen.getByText('test_key_789012')).toBeInTheDocument();
    });
  });

  it('shows correct status badges', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      const activeBadge = screen.getByText('active');
      const inactiveBadge = screen.getByText('inactive');

      expect(activeBadge).toBeInTheDocument();
      expect(inactiveBadge).toBeInTheDocument();
    });
  });

  it('opens create API key modal when button is clicked', async () => {
    render(<APIKeysManager />);

    const createButton = screen.getByRole('button', { name: /创建新密钥/i });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText('创建新的API密钥')).toBeInTheDocument();
      expect(screen.getByLabelText(/密钥名称/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/权限/i)).toBeInTheDocument();
    });
  });

  it('creates new API key successfully', async () => {
    render(<APIKeysManager />);

    // Open create modal
    const createButton = screen.getByRole('button', { name: /创建新密钥/i });
    await userEvent.click(createButton);

    // Fill form
    const nameInput = screen.getByLabelText(/密钥名称/i);
    await userEvent.type(nameInput, 'New Test Key');

    // Select permissions
    const chatPermission = screen.getByLabelText(/chat/i);
    await userEvent.click(chatPermission);

    const usagePermission = screen.getByLabelText(/usage/i);
    await userEvent.click(usagePermission);

    // Submit form
    const submitButton = screen.getByRole('button', { name: /创建/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('API密钥创建成功')).toBeInTheDocument();
    });
  });

  it('validates form fields', async () => {
    render(<APIKeysManager />);

    // Open create modal
    const createButton = screen.getByRole('button', { name: /创建新密钥/i });
    await userEvent.click(createButton);

    const submitButton = screen.getByRole('button', { name: /创建/i });

    // Try to submit without filling form
    await userEvent.click(submitButton);

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/请输入密钥名称/i)).toBeInTheDocument();
    });
  });

  it('deletes API key when delete button is clicked', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      const deleteButtons = screen.getAllByRole('button', { name: /删除/i });
      expect(deleteButtons.length).toBeGreaterThan(0);
    });

    const firstDeleteButton = screen.getAllByRole('button', { name: /删除/i })[0];
    await userEvent.click(firstDeleteButton);

    // Confirm deletion
    const confirmButton = screen.getByRole('button', { name: /确认删除/i });
    await userEvent.click(confirmButton);

    await waitFor(() => {
      expect(screen.getByText('API密钥删除成功')).toBeInTheDocument();
    });
  });

  it('shows API key details when view button is clicked', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      const viewButtons = screen.getAllByRole('button', { name: /查看/i });
      expect(viewButtons.length).toBeGreaterThan(0);
    });

    const firstViewButton = screen.getAllByRole('button', { name: /查看/i })[0];
    await userEvent.click(firstViewButton);

    await waitFor(() => {
      expect(screen.getByText(/API密钥详情/i)).toBeInTheDocument();
      expect(screen.getByText(/密钥ID/i)).toBeInTheDocument();
      expect(screen.getByText(/创建时间/i)).toBeInTheDocument();
    });
  });

  it('filters API keys by status', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByText(/筛选/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /全部/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /活跃/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /已禁用/i })).toBeInTheDocument();
    });
  });

  it('filters API keys correctly when status filter is clicked', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      const activeButton = screen.getByRole('button', { name: /活跃/i });
      expect(activeButton).toBeInTheDocument();
    });

    const activeButton = screen.getByRole('button', { name: /活跃/i });
    await userEvent.click(activeButton);

    await waitFor(() => {
      // Should only show active keys
      expect(screen.getByText('Test Key 1')).toBeInTheDocument();
      expect(screen.queryByText('Test Key 2')).not.toBeInTheDocument();
    });
  });

  it('searches API keys by name', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/搜索API密钥/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/搜索API密钥/i);
    await userEvent.type(searchInput, 'Test Key 1');

    await waitFor(() => {
      expect(screen.getByText('Test Key 1')).toBeInTheDocument();
      expect(screen.queryByText('Test Key 2')).not.toBeInTheDocument();
    });
  });

  it('exports API keys data', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      const exportButton = screen.getByRole('button', { name: /导出/i });
      expect(exportButton).toBeInTheDocument();
    });

    const exportButton = screen.getByRole('button', { name: /导出/i });
    await userEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText('数据导出成功')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    // Mock API error
    (fetch as jest.Mock).mockImplementationOnce(() => {
      return Promise.resolve({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ error: "Server error" })
      });
    });

    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByText(/加载失败/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /重试/i })).toBeInTheDocument();
    });
  });

  it('shows loading state while fetching', () => {
    // Mock slow API response
    (fetch as jest.Mock).mockImplementationOnce(() => {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            ok: true,
            json: () => Promise.resolve({
              success: true,
              data: mockAPIKeys
            })
          });
        }, 1000);
      });
    });

    render(<APIKeysManager />);

    // Initially should show loading state
    expect(screen.getByText(/加载中/i)).toBeInTheDocument();
  });

  it('handles pagination for large number of API keys', async () => {
    // Mock many API keys
    const manyAPIKeys = Array.from({ length: 50 }, (_, i) => ({
      id: `key-${i}`,
      name: `Test Key ${i + 1}`,
      key_prefix: `test_key_${i}`,
      is_active: i % 2 === 0,
      created_at: '2024-01-01T00:00:00Z',
      last_used: i % 3 === 0 ? '2024-01-01T12:00:00Z' : null
    }));

    (fetch as jest.Mock).mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: {
            api_keys: manyAPIKeys,
            pagination: {
              page: 1,
              limit: 20,
              total: 50,
              pages: 3
            }
          }
        })
      });
    });

    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByText('Test Key 1')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /下一页/i })).toBeInTheDocument();
    });
  });

  it('copies API key to clipboard when copy button is clicked', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn().mockResolvedValue(undefined)
      }
    });

    render(<APIKeysManager />);

    await waitFor(() => {
      const copyButtons = screen.getAllByRole('button', { name: /复制/i });
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    const firstCopyButton = screen.getAllByRole('button', { name: /复制/i })[0];
    await userEvent.click(firstCopyButton);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('test_key_')));
    });
  });

  it('shows empty state when no API keys exist', async () => {
    // Mock empty response
    (fetch as jest.Mock).mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: []
        })
      });
    });

    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByText(/暂无API密钥/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /创建新密钥/i })).toBeInTheDocument();
    });
  });

  it('displays last used date correctly', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByText(/2024-01-01/i)).toBeInTheDocument();
      expect(screen.getByText(/12:00/i)).toBeInTheDocument();
    });
  });

  it('shows permissions for each API key', async () => {
    // Mock API keys with permissions
    const mockKeysWithPermissions = mockAPIKeys.map(key => ({
      ...key,
      permissions: ['chat', 'usage']
    }));

    (fetch as jest.Mock).mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockKeysWithPermissions
        })
      });
    });

    render(<APIKeysManager />);

    await waitFor(() => {
      expect(screen.getByText(/权限/i)).toBeInTheDocument();
    });
  });

  it('regenerates API key when regenerate button is clicked', async () => {
    render(<APIKeysManager />);

    await waitFor(() => {
      const regenerateButtons = screen.getAllByRole('button', { name: /重新生成/i });
      expect(regenerateButtons.length).toBeGreaterThan(0);
    });

    const firstRegenerateButton = screen.getAllByRole('button', { name: /重新生成/i })[0];
    await userEvent.click(firstRegenerateButton);

    await waitFor(() => {
      expect(screen.getByText(/API密钥重新生成成功/i)).toBeInTheDocument();
    });
  });
});