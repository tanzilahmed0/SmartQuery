/**
 * Login Page Integration Tests
 * 
 * Integration tests for the login page and authentication flow.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi, type MockedFunction } from 'vitest';
import LoginPage from '@/app/login/page';
import { useAuth } from '@/components/auth/AuthProvider';

// Mock the auth context
vi.mock('@/components/auth/AuthProvider', () => ({
  useAuth: vi.fn(),
}));

// Mock Next.js navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockUseAuth = useAuth as MockedFunction<typeof useAuth>;

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
      setError: vi.fn(),
    });
  });

  describe('Page Rendering', () => {
    it('should render login page with SmartQuery branding', () => {
      render(<LoginPage />);

      expect(screen.getByText('Welcome to SmartQuery')).toBeInTheDocument();
      expect(screen.getByText('Sign in to access your data analysis dashboard')).toBeInTheDocument();
    });

    it('should render Google login buttons', () => {
      render(<LoginPage />);

      expect(screen.getByText('Continue with Google')).toBeInTheDocument();
    });

    it('should render features preview section', () => {
      render(<LoginPage />);

      expect(screen.getByText('What you can do with SmartQuery')).toBeInTheDocument();
      expect(screen.getByText('Upload CSVs Instantly')).toBeInTheDocument();
    });

    it('should render terms and privacy links', () => {
      render(<LoginPage />);

      expect(screen.getByText('Terms of Service')).toBeInTheDocument();
      expect(screen.getByText('Privacy Policy')).toBeInTheDocument();
    });
  });

  describe('Authentication States', () => {
    it('should redirect to dashboard when already authenticated', () => {

      mockUseAuth.mockReturnValue({
        user: { id: '1', name: 'Test User', email: 'test@example.com', avatar_url: '', created_at: '2024-01-01T00:00:00Z', last_sign_in_at: '2024-01-01T12:00:00Z' },
        accessToken: 'token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        setError: vi.fn(),
      });

      render(<LoginPage />);

      expect(mockPush).toHaveBeenCalledWith('/dashboard');
    });

    it('should show error message when authentication fails', () => {
      const mockSetError = vi.fn();
      mockUseAuth.mockReturnValue({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: 'Authentication failed',
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        setError: mockSetError,
      });

      render(<LoginPage />);

      expect(screen.getByText('Authentication Error')).toBeInTheDocument();
      expect(screen.getByText('Authentication failed')).toBeInTheDocument();
    });

    it.skip('should handle OAuth errors from URL parameters', () => {
      const mockSetError = vi.fn();
      mockUseAuth.mockReturnValue({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        setError: mockSetError,
      });

      // Mock useSearchParams to return an error

      render(<LoginPage />);

      expect(mockSetError).toHaveBeenCalledWith('Login failed: access_denied');
    });
  });

  describe('Button Interactions', () => {
    it('should handle Google login button clicks', () => {
      const originalLocation = window.location;
      delete (window as any).location;
      window.location = { href: '' } as any;

      render(<LoginPage />);

      const googleButton = screen.getByText('Continue with Google');
      fireEvent.click(googleButton);

      expect(window.location.href).toBe('http://localhost:8000/auth/google');

      Object.defineProperty(window, 'location', {
        value: originalLocation,
        writable: true,
      });
    });

    it('should handle alternative login button clicks', () => {
      const originalLocation = window.location;
      delete (window as any).location;
      window.location = { href: '' } as any;

      render(<LoginPage />);

      const altButton = screen.getByText('Dev Login (Bypass)');
      fireEvent.click(altButton);

      // The dev login button doesn't redirect, it just logs in directly
      // So we expect the href to remain empty
      expect(window.location.href).toBe('');

      Object.defineProperty(window, 'location', {
        value: originalLocation,
        writable: true,
      });
    });
  });

  describe('Page Layout', () => {
    it('should have proper responsive layout', () => {
      render(<LoginPage />);

      const container = screen.getByText('Welcome to SmartQuery').closest('div');
      expect(container).toHaveClass('text-center');
    });

    it('should have proper card styling', () => {
      render(<LoginPage />);

      // Find the card container by looking for the div with the card styling
      const cardContainer = screen.getByText('Continue with Google').closest('div[class*="bg-white"]');
      expect(cardContainer).toHaveClass('w-full', 'bg-white', 'dark:bg-gray-950', 'py-8', 'px-6', 'shadow-xl', 'rounded-2xl');
    });

    it('should have proper button styling', () => {
      render(<LoginPage />);

      const googleButton = screen.getByText('Continue with Google').closest('button');
      // Check that it's a button with some key classes
      expect(googleButton?.tagName).toBe('BUTTON');
      expect(googleButton).toHaveClass('btn');
    });
  });

  describe('Accessibility', () => {
    it('should have proper button roles', () => {
      render(<LoginPage />);

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2); // Two login buttons
    });

    it('should have proper heading structure', () => {
      render(<LoginPage />);

      const mainHeading = screen.getByRole('heading', { level: 2 });
      expect(mainHeading).toHaveTextContent('Welcome to SmartQuery');

      const subHeading = screen.getByRole('heading', { level: 3 });
      expect(subHeading).toHaveTextContent('What you can do with SmartQuery');
    });

    it('should have proper link elements', () => {
      render(<LoginPage />);

      const links = screen.getAllByRole('link');
      expect(links).toHaveLength(2); // Terms and Privacy links
    });
  });
}); 