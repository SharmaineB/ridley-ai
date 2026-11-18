'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, getUser, homeFor } from '@/lib/api';

export default function Index() {
  const router = useRouter();
  useEffect(() => {
    const u = getUser();
    router.replace(getToken() && u ? homeFor(u.role) : '/login');
  }, []);
  return null;
}
