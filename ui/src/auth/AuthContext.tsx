import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, clearApiCache, ACCOUNT_DELETED_EVENT, type AuthConfig, type Me } from "../api/client";
import { getIdToken, clearTokens, saveTokens } from "./tokens";
import { authConfigured, buildLoginUrl, buildGoogleLoginUrl, logoutUrl } from "./pkce";
import {
  cognitoSignIn,
  cognitoSignUp,
  cognitoConfirmSignUp,
  cognitoResendCode,
  cognitoForgotPassword,
  cognitoConfirmPassword,
  cognitoSignOut,
} from "./cognito";
import {
  clearLlmSettings,
  clearSessionLlmSettings,
  loadLlmSettings,
  saveLlmSettings,
  type LlmSettings,
} from "./llmKey";

interface AuthState {
  config: AuthConfig | null;
  configured: boolean; // false in local dev when the server has no Cognito settings
  signedIn: boolean;
  me: Me | null;
  meError: string | null;
  login: (returnTo?: string) => Promise<void>;
  loginWithGoogle: (returnTo?: string) => Promise<void>;
  signInWithSrp: (email: string, pass: string) => Promise<void>;
  signUp: (email: string, pass: string) => Promise<{ userConfirmed: boolean; userSub: string }>;
  confirmSignUp: (email: string, code: string) => Promise<void>;
  resendCode: (email: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  confirmNewPassword: (email: string, code: string, newPass: string) => Promise<void>;
  logout: () => void;
  completeSignIn: (idToken: string, accessToken: string | undefined, expiresIn: number) => Promise<Me | null>;
  refreshMe: () => Promise<Me | null>;
  forgetAccountLocally: () => void;
  llm: LlmSettings | null;
  setLlm: (s: LlmSettings | null) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [signedIn, setSignedIn] = useState(() => getIdToken() !== null);
  const [me, setMe] = useState<Me | null>(null);
  const [meError, setMeError] = useState<string | null>(null);
  const [llm, setLlmState] = useState<LlmSettings | null>(() => loadLlmSettings());

  useEffect(() => {
    api
      .getAuthConfig()
      .then((r) => setConfig(r.data))
      .catch(() => setConfig(null));
  }, []);

  // The API client clears tokens on 401 and fires this event.
  useEffect(() => {
    const onChange = () => {
      const has = getIdToken() !== null;
      setSignedIn(has);
      if (!has) {
        setMe(null);
      }
    };
    window.addEventListener("tf-auth-changed", onChange);
    return () => window.removeEventListener("tf-auth-changed", onChange);
  }, []);

  const refreshMe = useCallback(async () => {
    if (!getIdToken()) {
      setSignedIn(false);
      setMe(null);
      return null;
    }
    try {
      const r = await api.getMe();
      setMe(r.data);
      setMeError(null);
      return r.data;
    } catch {
      setMeError("Could not load your account.");
      setSignedIn(getIdToken() !== null);
      return null;
    }
  }, []);

  useEffect(() => {
    if (signedIn && !me) void refreshMe();
  }, [signedIn, me, refreshMe]);

  const login = useCallback(
    async (returnTo = "/app") => {
      if (!authConfigured(config)) return;
      window.location.assign(await buildLoginUrl(config, returnTo));
    },
    [config]
  );

  const loginWithGoogle = useCallback(
    async (returnTo = "/app") => {
      if (!authConfigured(config)) return;
      window.location.assign(await buildGoogleLoginUrl(config, returnTo));
    },
    [config]
  );

  const completeSignIn = useCallback(
    async (idToken: string, accessToken: string | undefined, expiresIn: number) => {
      saveTokens(idToken, accessToken, expiresIn);
      setSignedIn(true);
      return refreshMe();
    },
    [refreshMe]
  );

  const signInWithSrp = useCallback(
    async (email: string, pass: string) => {
      if (!config) throw new Error("Authentication is not configured.");
      const res = await cognitoSignIn(config, email, pass);
      await completeSignIn(res.idToken, res.accessToken, res.expiresInSec);
    },
    [config, completeSignIn]
  );

  const signUp = useCallback(
    async (email: string, pass: string) => {
      if (!config) throw new Error("Authentication is not configured.");
      return cognitoSignUp(config, email, pass);
    },
    [config]
  );

  const confirmSignUp = useCallback(
    async (email: string, code: string) => {
      if (!config) throw new Error("Authentication is not configured.");
      return cognitoConfirmSignUp(config, email, code);
    },
    [config]
  );

  const resendCode = useCallback(
    async (email: string) => {
      if (!config) throw new Error("Authentication is not configured.");
      return cognitoResendCode(config, email);
    },
    [config]
  );

  const forgotPassword = useCallback(
    async (email: string) => {
      if (!config) throw new Error("Authentication is not configured.");
      return cognitoForgotPassword(config, email);
    },
    [config]
  );

  const confirmNewPassword = useCallback(
    async (email: string, code: string, newPass: string) => {
      if (!config) throw new Error("Authentication is not configured.");
      return cognitoConfirmPassword(config, email, code, newPass);
    },
    [config]
  );

  // Session key goes with the session; a key remembered on this device stays until the user forgets it.
  const dropSession = useCallback(() => {
    clearTokens();
    clearApiCache();
    clearSessionLlmSettings();
    setSignedIn(false);
    setMe(null);
    setLlmState(loadLlmSettings());
  }, []);

  const logout = useCallback(() => {
    cognitoSignOut(config);
    dropSession();
    if (authConfigured(config)) {
      window.location.assign(logoutUrl(config));
    } else {
      window.location.assign("/");
    }
  }, [config, dropSession]);

  // After account deletion nothing of the user stays in this browser.
  const forgetAccountLocally = useCallback(() => {
    clearLlmSettings();
    dropSession();
  }, [dropSession]);

  useEffect(() => {
    const onAccountDeleted = () => {
      cognitoSignOut(config);
      forgetAccountLocally();
    };
    window.addEventListener(ACCOUNT_DELETED_EVENT, onAccountDeleted);
    return () => window.removeEventListener(ACCOUNT_DELETED_EVENT, onAccountDeleted);
  }, [config, forgetAccountLocally]);

  const setLlm = useCallback((s: LlmSettings | null) => {
    if (s) saveLlmSettings(s);
    else clearLlmSettings();
    setLlmState(s);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      config,
      configured: authConfigured(config),
      signedIn,
      me,
      meError,
      login,
      loginWithGoogle,
      signInWithSrp,
      signUp,
      confirmSignUp,
      resendCode,
      forgotPassword,
      confirmNewPassword,
      logout,
      completeSignIn,
      refreshMe,
      forgetAccountLocally,
      llm,
      setLlm,
    }),
    [
      config,
      signedIn,
      me,
      meError,
      login,
      loginWithGoogle,
      signInWithSrp,
      signUp,
      confirmSignUp,
      resendCode,
      forgotPassword,
      confirmNewPassword,
      logout,
      completeSignIn,
      refreshMe,
      forgetAccountLocally,
      llm,
      setLlm,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
