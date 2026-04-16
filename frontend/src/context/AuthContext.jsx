import { createContext, useEffect, useMemo, useState } from "react";
import { getMe, login as apiLogin, verify2fa as apiVerify2fa } from "../api/authApi";
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
        if (error?.response?.status === 401 || error?.response?.status === 403) {
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

  /**
   * Step 1: authenticate with email/password.
   * Returns { requires_2fa, session_token, demo_otp } if 2FA is needed.
   */
  const login = async (email, password) => {
    const response = await apiLogin(email, password);
    if (response.requires_2fa) {
      // Don't set token yet — user must complete 2FA
      return response;
    }
    // Fallback: if server ever returns access_token directly (unlikely)
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    const me = await getMe();
    setUser(me);
    return response;
  };

  /**
   * Step 2: verify OTP and get final JWT.
   */
  const verify2fa = async (sessionToken, otpCode) => {
    const response = await apiVerify2fa(sessionToken, otpCode);
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    const me = await getMe();
    setUser(me);
    return response;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ token, user, loading, login, verify2fa, logout }),
    [token, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
