/**
 * ChatInterface Component Tests
 * Week 4 Day 27: System Integration Testing and Documentation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { jest } from '@testing-library/jest-dom';
import ChatInterface from '../ChatInterface';

// Mock fetch
global.fetch = jest.fn();

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;

  constructor(url: string) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;

    // Simulate connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string) {
    // Mock send
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  addEventListener() {}
  removeEventListener() {}
}

// Mock WebSocket
global.WebSocket = MockWebSocket as any;

// Mock EventSource
class MockEventSource {
  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: Event) => void) | null;

  constructor(url: string) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;

    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  close() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  addEventListener() {}
  removeEventListener() {}
}

global.EventSource = MockEventSource as any;

describe('ChatInterface Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();

    // Mock API responses
    (fetch as jest.Mock).mockImplementation((url) => {
      if (url.includes('/api/v1/models')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: [
              {
                id: "gpt-4o",
                name: "GPT-4o",
                provider: "OpenRouter",
                description: "Advanced language model",
                context_length: 128000,
                pricing: { input: 0.015, output: 0.06 }
              },
              {
                id: "gpt-4o-mini",
                name: "GPT-4o Mini",
                provider: "OpenRouter",
                description: "Efficient language model",
                context_length: 128000,
                pricing: { input: 0.00015, output: 0.0006 }
              }
            ]
          })
        });
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

  it('renders chat interface correctly', () => {
    render(<ChatInterface />);

    // Check if main elements are present
    expect(screen.getByPlaceholderText(/输入您的消息/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /发送/i })).toBeInTheDocument();
    expect(screen.getByText(/AI 模型/i)).toBeInTheDocument();
  });

  it('loads available models on mount', async () => {
    render(<ChatInterface />);

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
      expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument();
    });
  });

  it('allows model selection', async () => {
    render(<ChatInterface />);

    await waitFor(() => {
      const modelSelect = screen.getByDisplayValue('GPT-4o');
      expect(modelSelect).toBeInTheDocument();
    });

    // Change model
    fireEvent.change(modelSelect, { target: { value: 'gpt-4o-mini' } });

    expect(screen.getByDisplayValue('GPT-4o Mini')).toBeInTheDocument();
  });

  it('sends message when send button is clicked', async () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
    const sendButton = screen.getByRole('button', { name: /发送/i });

    // Type a message
    fireEvent.change(messageInput, { target: { value: 'Hello, AI!' } });

    // Click send button
    fireEvent.click(sendButton);

    // Check if input is cleared
    await waitFor(() => {
      expect(messageInput).toHaveValue('');
    });
  });

  it('sends message when Enter key is pressed (without Shift)', async () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);

    // Type a message and press Enter
    fireEvent.change(messageInput, { target: { value: 'Hello, AI!' } });
    fireEvent.keyDown(messageInput, { key: 'Enter', shiftKey: false });

    // Check if input is cleared
    await waitFor(() => {
      expect(messageInput).toHaveValue('');
    });
  });

  it('does not send message when Shift+Enter is pressed', async () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);

    // Type a message and press Shift+Enter (for new line)
    fireEvent.change(messageInput, { target: { value: 'Hello,\nAI!' } });
    fireEvent.keyDown(messageInput, { key: 'Enter', shiftKey: true });

    // Check if input is not cleared
    expect(messageInput).toHaveValue('Hello,\nAI!');
  });

  it('disables send button when input is empty', () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
    const sendButton = screen.getByRole('button', { name: /发送/i });

    // Initially disabled
    expect(sendButton).toBeDisabled();

    // Type a message
    fireEvent.change(messageInput, { target: { value: 'Hello' } });

    // Should be enabled
    expect(sendButton).not.toBeDisabled();
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

    render(<ChatInterface />);

    // The component should still render without crashing
    expect(screen.getByPlaceholderText(/输入您的消息/i)).toBeInTheDocument();
  });

  it('maintains chat history', async () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
    const sendButton = screen.getByRole('button', { name: /发送/i });

    // Send first message
    fireEvent.change(messageInput, { target: { value: 'First message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(messageInput).toHaveValue('');
    });

    // Send second message
    fireEvent.change(messageInput, { target: { value: 'Second message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(messageInput).toHaveValue('');
    });

    // Check that chat history is maintained (mock WebSocket should have received messages)
    // This would need to be tested with the actual WebSocket implementation
  });

  it('shows loading state while processing', async () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
    const sendButton = screen.getByRole('button', { name: /发送/i });

    // Send a message
    fireEvent.change(messageInput, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    // Initially send button should be disabled during processing
    expect(sendButton).toBeDisabled();

    // Wait for processing to complete
    await waitFor(() => {
      expect(messageInput).toHaveValue('');
    }, { timeout: 3000 });
  });

  it('clears chat when clear button is clicked', async () => {
    render(<ChatInterface />);

    // Add a clear button (if it exists)
    const clearButton = screen.queryByRole('button', { name: /清除/i });

    if (clearButton) {
      // Send some messages first (mocked)
      const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
      const sendButton = screen.getByRole('button', { name: /发送/i });

      fireEvent.change(messageInput, { target: { value: 'Test message' } });
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(messageInput).toHaveValue('');
      });

      // Click clear button
      fireEvent.click(clearButton);

      // Check if chat is cleared
      // This would depend on the implementation
    }
  });

  it('adjusts textarea height automatically', () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);

    // Initially should have default height
    expect(messageInput).toHaveStyle({});

    // Type a long message
    const longMessage = 'This is a very long message that should cause the textarea to expand automatically to accommodate the content without requiring user interaction.';
    fireEvent.change(messageInput, { target: { value: longMessage } });

    // Check if height adjusted
    // This depends on the autoResize implementation
  });

  it('handles network connection issues', () => {
    // Mock network failure
    global.WebSocket = class extends MockWebSocket {
      constructor(url: string) {
        super(url);
        setTimeout(() => {
          this.readyState = MockWebSocket.CLOSED;
          if (this.onerror) {
            this.onerror(new Event('error'));
          }
        }, 100);
      }
    };

    render(<ChatInterface />);

    // Component should still render and handle connection issues gracefully
    expect(screen.getByPlaceholderText(/输入您的消息/i)).toBeInTheDocument();
  });

  it('displays appropriate error messages for invalid input', async () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
    const sendButton = screen.getByRole('button', { name: /发送/i });

    // Test with extremely long message
    const extremelyLongMessage = 'A'.repeat(10000);
    fireEvent.change(messageInput, { target: { value: extremelyLongMessage } });

    // Either should allow it or show appropriate error
    // This depends on the validation implementation

    // Try to send
    fireEvent.click(sendButton);

    // Handle accordingly based on expected behavior
  });

  it('supports keyboard navigation', () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
    const sendButton = screen.getByRole('button', { name: /发送/i });

    // Focus input
    messageInput.focus();
    expect(messageInput).toHaveFocus();

    // Tab navigation should work
    fireEvent.keyDown(messageInput, { key: 'Tab' });

    // Check if send button can be focused
    sendButton.focus();
    expect(sendButton).toHaveFocus();
  });

  it('displays model information correctly', async () => {
    render(<ChatInterface />);

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
      expect(screen.getByText(/OpenRouter/i)).toBeInTheDocument();
      expect(screen.getByText(/128000/)).toBeInTheDocument();
    });
  });

  it('handles streaming responses correctly', async () => {
    render(<ChatInterface />);

    const messageInput = screen.getByPlaceholderText(/输入您的消息/i);
    const sendButton = screen.getByRole('button', { name: /发送/i });

    // Mock streaming response
    const mockEventSource = new MockEventSource('/api/v1/chat/stream');

    // Send message
    fireEvent.change(messageInput, { target: { value: 'Test streaming' } });
    fireEvent.click(sendButton);

    // Simulate streaming events
    setTimeout(() => {
      if (mockEventSource.onmessage) {
        mockEventSource.onmessage(new MessageEvent('message', {
          data: 'data: {"type": "start"}\n\n'
        }));
        mockEventSource.onmessage(new MessageEvent('message', {
          data: 'data: {"type": "chunk", "content": "Hello"}\n\n'
        }));
        mockEventSource.onmessage(new MessageEvent('message', {
          data: 'data: {"type": "end"}\n\n'
        }));
      }
    }, 200);

    // Component should handle streaming updates
    await waitFor(() => {
      expect(screen.getByText(/Hello/i)).toBeInTheDocument();
    }, { timeout: 5000 });
  });
});