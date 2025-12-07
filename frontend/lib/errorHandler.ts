/**
 * Error handling utilities for IPAM Frontend
 * Provides standardized error processing and user-friendly messages
 */

export interface ApiError {
  error_code?: string;
  message: string;
  details?: Record<string, any>;
  request_id?: string;
  status?: number;
}

export interface RequestError {
  type: 'network' | 'validation' | 'conflict' | 'not_found' | 'server' | 'unknown';
  message: string;
  details?: Record<string, any>;
  status_code?: number;
  is_recoverable: boolean;
}

/**
 * Parse an API error response and convert to user-friendly message
 */
export function parseApiError(error: any): RequestError {
  const status = error.response?.status || error.status || 500;

  // Handle timeout/network errors
  if (error.message === 'Network Error' || error.code === 'ECONNABORTED') {
    return {
      type: 'network',
      message: 'Network connection failed. Please check your internet connection.',
      status_code: status,
      is_recoverable: true,
    };
  }

  // Handle validation errors (400)
  if (status === 400) {
    const detail = error.response?.data?.detail || error.message;
    return {
      type: 'validation',
      message: `Invalid input: ${detail}`,
      details: error.response?.data?.details,
      status_code: status,
      is_recoverable: true,
    };
  }

  // Handle conflict errors (409)
  if (status === 409) {
    const detail = error.response?.data?.detail || 'Resource already exists or has a conflict';
    return {
      type: 'conflict',
      message: detail,
      details: error.response?.data?.details,
      status_code: status,
      is_recoverable: true,
    };
  }

  // Handle not found errors (404)
  if (status === 404) {
    const detail = error.response?.data?.detail || 'Resource not found';
    return {
      type: 'not_found',
      message: detail,
      status_code: status,
      is_recoverable: true,
    };
  }

  // Handle insufficient storage (507)
  if (status === 507) {
    return {
      type: 'validation',
      message: 'No available IP addresses in this subnet',
      status_code: status,
      is_recoverable: true,
    };
  }

  // Handle server errors (500+)
  if (status >= 500) {
    return {
      type: 'server',
      message: 'Server error occurred. Please try again later.',
      details: { status },
      status_code: status,
      is_recoverable: true,
    };
  }

  // Unknown error
  return {
    type: 'unknown',
    message: error.message || 'An unexpected error occurred',
    status_code: status,
    is_recoverable: false,
  };
}

/**
 * Get user-friendly message for different error types
 */
export function getUserFriendlyMessage(error: RequestError): string {
  switch (error.type) {
    case 'network':
      return 'Network connection failed. Please check your internet and try again.';
    case 'validation':
      return error.message;
    case 'conflict':
      return `Could not create resource: ${error.message}`;
    case 'not_found':
      return error.message;
    case 'server':
      return 'Server encountered an error. Please try again later.';
    default:
      return error.message || 'An unexpected error occurred';
  }
}

/**
 * Detailed error logger for development/debugging
 */
export function logError(error: any, context: string): void {
  if (typeof window !== 'undefined') {
    console.error(`[${context}]`, {
      error,
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      stack: error.stack,
      timestamp: new Date().toISOString(),
    });
  }
}

/**
 * Format error details for display
 */
export function formatErrorDetails(error: RequestError): string {
  const parts = [error.message];

  if (error.details) {
    const detailsStr = Object.entries(error.details)
      .filter(([_, v]) => v != null)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ');

    if (detailsStr) {
      parts.push(`(${detailsStr})`);
    }
  }

  return parts.join(' ');
}

/**
 * Check if an error is recoverable (user can retry)
 */
export function isRecoverableError(error: any): boolean {
  if (error.is_recoverable !== undefined) {
    return error.is_recoverable;
  }

  const status = error.response?.status || error.status;
  // 4xx and network errors are typically user-recoverable
  // 5xx may also be transient
  return (status >= 400 && status < 500) || status >= 500;
}

/**
 * Create a structured error with retry info
 */
export function createRetryableError(
  error: any,
  context: string,
  retryCount: number = 0,
  maxRetries: number = 3
): RequestError & { canRetry: boolean; retryCount: number; maxRetries: number } {
  const parsed = parseApiError(error);
  return {
    ...parsed,
    canRetry: retryCount < maxRetries && isRecoverableError(error),
    retryCount,
    maxRetries,
  };
}
