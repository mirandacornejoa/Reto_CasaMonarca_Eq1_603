import { createContext, useEffect, useMemo, useState } from "react";
import { getMe, login as apiLogin } from "../api/authApi";
import { TOKEN_KEY } from "../constants";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSession = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const me = await getMe();
        setUser(me);
      } catch (error) {
        if (error?.response?.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
        }
      } finally {
        setLoading(false);
      }
    };

    loadSession();
  }, [token]);

  const login = async (email, password) => {
    const response = await apiLogin(email, password);
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    const me = await getMe();
    setUser(me);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ token, user, loading, login, logout }),
    [token, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
