import { useEffect, useRef, useState } from 'react';

export function useCountdown(duration: number, active: boolean, resetKey: string | number, onExpire?: () => void) {
  const [remaining, setRemaining] = useState(duration);
  const onExpireRef = useRef(onExpire);
  const expiredRef = useRef(false);
  onExpireRef.current = onExpire;

  useEffect(() => {
    setRemaining(duration);
    expiredRef.current = false;
  }, [duration, resetKey]);

  useEffect(() => {
    if (!active || remaining <= 0) return;
    const interval = window.setInterval(() => {
      setRemaining(current => {
        if (current <= 1) {
          if (!expiredRef.current) {
            expiredRef.current = true;
            onExpireRef.current?.();
          }
          return 0;
        }
        return current - 1;
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [active, remaining]);

  return remaining;
}
