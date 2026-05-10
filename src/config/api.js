export const DEFAULT_API_URL = 'https://crewops.charchitbansal.com';

export const API_URL = import.meta.env.VITE_API_URL || DEFAULT_API_URL;

export const getDefaultWebSocketUrl = (path = '/ws/logs') => {
  try {
    const url = new URL(API_URL);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = path;
    url.search = '';
    url.hash = '';
    return url.toString();
  } catch {
    return 'wss://crewops.charchitbansal.com/ws/logs';
  }
};
