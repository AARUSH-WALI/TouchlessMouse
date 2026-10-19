/**
 * Daily Touchless Gesture Quota Utility
 * Provides optional daily quota limiter via localStorage or unlimited access.
 */
export const getTouchlessUsage = (isPremium = true) => {
  if (isPremium) {
    return { count: 0, limit: Infinity, remaining: Infinity, exhausted: false, isPremium: true };
  }
  const today = new Date().toISOString().slice(0, 10);
  const key = `touchless_usage_${today}`;
  const count = parseInt(localStorage.getItem(key) || '0', 10);
  const limit = 100;
  return {
    count,
    limit,
    remaining: Math.max(0, limit - count),
    exhausted: count >= limit,
    isPremium: false,
  };
};

export const consumeTouchlessGesture = (isPremium = true) => {
  if (isPremium) return { allowed: true, count: 0, remaining: Infinity };
  const today = new Date().toISOString().slice(0, 10);
  const key = `touchless_usage_${today}`;
  let count = parseInt(localStorage.getItem(key) || '0', 10);
  if (count >= 100) return { allowed: false, count, remaining: 0 };
  count += 1;
  localStorage.setItem(key, count.toString());
  return { allowed: true, count, remaining: 100 - count };
};
