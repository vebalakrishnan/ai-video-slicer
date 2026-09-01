import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios';

// An axios request config, extended with the retry flag we stamp on
// requests after a single 401 -> refresh -> retry cycle so we never
// loop infinitely on a permanently invalid refresh token.
interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

const API_BASE_URL = `${import.meta.env.VITE_API_URL}/api/v1`;

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post<TokenPair>(
          `${API_BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken },
        );

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export default api;
