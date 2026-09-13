import { useCallback, useEffect, useState } from 'react';
import { Stats, emptyStats, fetchStats } from 'api/gateway';

/** Polls the gateway's /stats every `intervalMs` and exposes a manual refresh. */
export default function useStats(intervalMs = 1500) {
  const [stats, setStats] = useState<Stats>(emptyStats);
  const [online, setOnline] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setStats(await fetchStats());
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

  return { stats, online, refresh };
}
