/**
 * Performance Dashboard Page
 * Admin-only performance monitoring interface
 */

'use client';

import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, Suspense } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';

// Lazy load the performance dashboard for better initial loading
const PerformanceDashboard = dynamic(
  () => import('@/components/performance/PerformanceDashboard'),
  {
    loading: () => (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin mr-2" />
          Loading performance dashboard...
        </CardContent>
      </Card>
    ),
    ssr: false
  }
);

export default function PerformancePage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && (!user || !user.isAdmin)) {
      router.push('/dashboard');
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  if (!user || !user.isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Suspense fallback={
        <div className="p-6">
          <Card>
            <CardContent className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin mr-2" />
              Loading performance monitoring...
            </CardContent>
          </Card>
        </div>
      }>
        <PerformanceDashboard />
      </Suspense>
    </div>
  );
}