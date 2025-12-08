'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    // Allow access to login page without token
    if (pathname === '/login') {
      setAuthorized(true);
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
    } else {
      setAuthorized(true);
    }
  }, [router, pathname]);

  // Optionally show nothing while checking to prevent flash of content
  if (!authorized && pathname !== '/login') {
    return null; 
  }

  return <>{children}</>;
}
