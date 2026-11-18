'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, getUser, homeFor } from './api';

export function useAuth(roles) {
  const router = useRouter();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = getToken();
    const u = getUser();
    if (!token || !u) {
      router.replace('/login');
      return;
    }
    if (roles && !roles.includes(u.role)) {
      router.replace(homeFor(u.role));
      return;
    }
    setUser(u);
  }, []);

  return user;
}
