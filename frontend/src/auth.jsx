import { createContext, useContext, useState } from "react";
import { api, clearSession, getStoredUser, storeSession } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser);

  async function signIn(username, password) {
    const data = await api.login(username, password);
    const session = { username: data.username, role: data.role };
    storeSession(data.access_token, session);
    setUser(session);
    return session;
  }

  function signOut() {
    clearSession();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

// Which roles may open which screens. This mirrors the backend's RBAC rules;
// the backend is still the real check, this only keeps the UI tidy.
export const STAFF = ["ANALYST", "COMPLIANCE", "ADMIN"];

export function canSee(role, allowed) {
  return allowed.includes(role);
}
