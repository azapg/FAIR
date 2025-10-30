import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { toast } from 'sonner';

interface VersionInfo {
  current: string;
  latest: string;
  outdated: boolean;
}

const VERSION_CHECK_KEY = 'fair_version_check_done';

const fetchVersion = async (): Promise<VersionInfo> => {
  const res = await api.get('/version');
  return res.data;
};

export const useVersionCheck = () => {
  const { data } = useQuery({
    queryKey: ['version'],
    queryFn: fetchVersion,
    staleTime: 6 * 60 * 60 * 1000, // 6 hours
    retry: false, // Don't retry on failure
  });

  useEffect(() => {
    // Only check once per session
    if (typeof window === 'undefined') return;
    
    const hasChecked = sessionStorage.getItem(VERSION_CHECK_KEY);
    if (hasChecked) return;

    // If we have data and backend says it's outdated
    if (data && data.outdated) {
      toast.info('New FAIR version available', {
        description: `Version ${data.latest} is available. Update with: pip install -U fair-platform`,
        duration: 10000,
      });
    }

    // Mark as checked for this session (even if not outdated)
    if (data) {
      sessionStorage.setItem(VERSION_CHECK_KEY, 'true');
    }
  }, [data]);

  // Silent failure - don't expose errors to UI
  return { version: data };
};
