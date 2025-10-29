import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { toast } from 'sonner';

interface VersionInfo {
  current: string;
  latest: string;
}

const VERSION_CHECK_KEY = 'fair_version_check_done';

const fetchVersion = async (): Promise<VersionInfo> => {
  const res = await api.get('/version');
  return res.data;
};

export const useVersionCheck = () => {
  const { data, isError } = useQuery({
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

    // If we have data and there's a new version available
    if (data && data.current !== data.latest) {
      try {
        // Simple version comparison
        const currentParts = data.current.split(/[.-]/).map(p => parseInt(p, 10) || 0);
        const latestParts = data.latest.split(/[.-]/).map(p => parseInt(p, 10) || 0);
        
        // Compare major, minor, patch
        let isNewer = false;
        for (let i = 0; i < Math.max(currentParts.length, latestParts.length); i++) {
          const current = currentParts[i] || 0;
          const latest = latestParts[i] || 0;
          if (latest > current) {
            isNewer = true;
            break;
          } else if (latest < current) {
            break;
          }
        }

        if (isNewer) {
          toast.info('New FAIR version available', {
            description: `Version ${data.latest} is available. Update with: pip install -U fair-platform`,
            duration: 10000,
          });
        }
      } catch {
        // Silent failure on version comparison error
      }

      // Mark as checked for this session
      sessionStorage.setItem(VERSION_CHECK_KEY, 'true');
    }
  }, [data]);

  // Silent failure - don't expose errors to UI
  return { version: data };
};
