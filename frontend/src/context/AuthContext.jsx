import { createContext, useContext, useEffect, useState } from "react";
import apiClient from "../lib/apiClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    apiClient
      .get("/api/auth/me")
      .then((response) => setCurrentUser(response.data))
      .catch(() => {
        localStorage.removeItem("access_token");
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    // /api/auth/login expects an OAuth2 form body, not JSON.
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);
    const { data } = await apiClient.post("/api/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    localStorage.setItem("access_token", data.access_token);
    const { data: user } = await apiClient.get("/api/auth/me");
    setCurrentUser(user);
    return user;
  }

  async function register(payload) {
    await apiClient.post("/api/auth/register", payload);
    return login(payload.username, payload.password);
  }

  function logout() {
    localStorage.removeItem("access_token");
    setCurrentUser(null);
  }

  const value = {
    currentUser,
    loading,
    isStaff: currentUser?.role === "officer" || currentUser?.role === "admin",
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
