'use client';
import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { createPortal } from 'react-dom';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  addToast: (message: string, type: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);

    // Auto dismiss
    setTimeout(() => {
      removeToast(id);
    }, 4000);
  }, [removeToast]);

  const success = (msg: string) => addToast(msg, 'success');
  const error = (msg: string) => addToast(msg, 'error');
  const info = (msg: string) => addToast(msg, 'info');

  return (
    <ToastContext.Provider value={{ addToast, success, error, info }}>
      {children}
      {typeof document !== 'undefined' && createPortal(
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-full max-w-sm px-4 sm:px-0 pointer-events-none">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`
                pointer-events-auto flex items-center gap-3 w-full rounded-lg bg-white p-4 shadow-lg border ring-1 ring-black/5 
                animate-in slide-in-from-bottom-5 fade-in duration-300
                ${toast.type === 'success' ? 'border-green-100' : ''}
                ${toast.type === 'error' ? 'border-red-100' : ''}
              `}
            >
              <div className="flex-shrink-0">
                {toast.type === 'success' && <CheckCircle size={20} className="text-green-500" />}
                {toast.type === 'error' && <AlertCircle size={20} className="text-red-500" />}
                {toast.type === 'info' && <Info size={20} className="text-blue-500" />}
              </div>
              <p className="flex-1 text-sm font-medium text-gray-900">{toast.message}</p>
              <button
                onClick={() => removeToast(toast.id)}
                className="flex-shrink-0 text-gray-400 hover:text-gray-500"
              >
                <X size={16} />
              </button>
            </div>
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
