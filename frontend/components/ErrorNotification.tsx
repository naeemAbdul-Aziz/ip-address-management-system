/**
 * Error Boundary Component for IPAM Frontend
 * Displays errors with proper styling and recovery actions
 */

'use client';

import React, { ReactNode, useState, useCallback } from 'react';
import { AlertCircle, RefreshCw, X } from 'lucide-react';
import { RequestError, getUserFriendlyMessage, formatErrorDetails } from '@/lib/errorHandler';

interface ErrorNotificationProps {
  error: RequestError | string;
  onDismiss?: () => void;
  onRetry?: () => Promise<void>;
  isRetrying?: boolean;
  autoHideDuration?: number;
}

/**
 * Reusable Error Notification Component
 */
export function ErrorNotification({
  error,
  onDismiss,
  onRetry,
  isRetrying = false,
  autoHideDuration = 0,
}: ErrorNotificationProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [isRetryLoading, setIsRetryLoading] = useState(false);

  React.useEffect(() => {
    if (autoHideDuration > 0) {
      const timer = setTimeout(() => {
        handleDismiss();
      }, autoHideDuration);
      return () => clearTimeout(timer);
    }
  }, [autoHideDuration]);

  if (!isVisible) {
    return null;
  }

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  const handleRetry = async () => {
    if (onRetry) {
      setIsRetryLoading(true);
      try {
        await onRetry();
        setIsVisible(false);
      } finally {
        setIsRetryLoading(false);
      }
    }
  };

  const errorMessage =
    typeof error === 'string' ? error : getUserFriendlyMessage(error);
  const errorDetails =
    typeof error === 'object' && error !== null
      ? formatErrorDetails(error as RequestError)
      : null;

  const isRecoverable =
    typeof error === 'object' && error !== null && (error as RequestError).is_recoverable;

  return (
    <div className="animate-in slide-in-from-top-2 duration-300 fade-in">
      <div className="mx-4 md:mx-0 mb-4 p-4 bg-red-50 border border-red-200 rounded-lg shadow-sm">
        <div className="flex gap-3">
          <AlertCircle className="shrink-0 text-red-600 mt-0.5" size={20} />
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-red-900 text-sm md:text-base">
              Error
            </h3>
            <p className="text-red-800 text-sm mt-1">{errorMessage}</p>
            {errorDetails && errorDetails !== errorMessage && (
              <p className="text-red-700 text-xs mt-2 opacity-75">{errorDetails}</p>
            )}
          </div>
          <div className="flex gap-2 shrink-0">
            {onRetry && isRecoverable && (
              <button
                onClick={handleRetry}
                disabled={isRetryLoading || isRetrying}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-100 hover:bg-red-200 text-red-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Retry this operation"
                aria-label="Retry operation"
              >
                <RefreshCw size={14} className={isRetryLoading ? 'animate-spin' : ''} />
                Retry
              </button>
            )}
            <button
              onClick={handleDismiss}
              className="inline-flex items-center justify-center p-1.5 text-red-600 hover:bg-red-100 rounded transition-colors"
              title="Dismiss this error"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Success Notification Component
 */
export function SuccessNotification({
  message,
  onDismiss,
  autoHideDuration = 3000,
}: {
  message: string;
  onDismiss?: () => void;
  autoHideDuration?: number;
}) {
  const [isVisible, setIsVisible] = useState(true);

  React.useEffect(() => {
    if (autoHideDuration > 0) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        onDismiss?.();
      }, autoHideDuration);
      return () => clearTimeout(timer);
    }
  }, [autoHideDuration, onDismiss]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="animate-in slide-in-from-top-2 duration-300 fade-in">
      <div className="mx-4 md:mx-0 mb-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg shadow-sm">
        <div className="flex gap-3">
          <div className="shrink-0 w-5 h-5 rounded-full bg-emerald-500 mt-0.5" />
          <div className="flex-1">
            <p className="text-emerald-800 text-sm font-medium">{message}</p>
          </div>
          <button
            onClick={() => setIsVisible(false)}
            className="text-emerald-600 hover:bg-emerald-100 p-1.5 rounded transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Warning Notification Component
 */
export function WarningNotification({
  message,
  onDismiss,
  autoHideDuration = 5000,
}: {
  message: string;
  onDismiss?: () => void;
  autoHideDuration?: number;
}) {
  const [isVisible, setIsVisible] = useState(true);

  React.useEffect(() => {
    if (autoHideDuration > 0) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        onDismiss?.();
      }, autoHideDuration);
      return () => clearTimeout(timer);
    }
  }, [autoHideDuration, onDismiss]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="animate-in slide-in-from-top-2 duration-300 fade-in">
      <div className="mx-4 md:mx-0 mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg shadow-sm">
        <div className="flex gap-3">
          <AlertCircle className="shrink-0 text-amber-600 mt-0.5" size={20} />
          <div className="flex-1">
            <p className="text-amber-800 text-sm font-medium">{message}</p>
          </div>
          <button
            onClick={() => setIsVisible(false)}
            className="text-amber-600 hover:bg-amber-100 p-1.5 rounded transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary Class Component for catching React errors
 */
export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
              <div className="flex justify-center mb-4">
                <AlertCircle className="text-red-600" size={48} />
              </div>
              <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">
                Something went wrong
              </h1>
              <p className="text-gray-600 text-center mb-6">
                {this.state.error?.message || 'An unexpected error occurred'}
              </p>
              <button
                onClick={this.handleReset}
                className="w-full bg-black text-white py-2 rounded-lg font-medium hover:bg-gray-800 transition-colors"
              >
                Try again
              </button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}

/**
 * Hook for managing form errors with notifications
 */
export function useFormError() {
  const [error, setError] = useState<RequestError | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const handleError = useCallback((err: any) => {
    const { parseApiError } = require('@/lib/errorHandler');
    const parsedError = parseApiError(err);
    setError(parsedError);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const handleRetry = useCallback(async (fn: () => Promise<void>) => {
    setIsRetrying(true);
    try {
      await fn();
      setError(null);
    } catch (err) {
      handleError(err);
    } finally {
      setIsRetrying(false);
    }
  }, [handleError]);

  return {
    error,
    isRetrying,
    handleError,
    clearError,
    handleRetry,
  };
}
