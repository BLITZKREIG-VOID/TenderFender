import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
  type ICognitoStorage,
} from "amazon-cognito-identity-js";
import type { AuthConfig } from "../api/client";

// Storage adapter that strictly confines Cognito keys to sessionStorage.
// Never touches localStorage, so credentials/tokens evaporate when the session ends.
export const sessionCognitoStorage: ICognitoStorage = {
  setItem(key: string, value: string): void {
    try {
      sessionStorage.setItem(key, value);
    } catch {
      // Ignore quota/private browsing errors
    }
  },
  getItem(key: string): string | null {
    try {
      return sessionStorage.getItem(key);
    } catch {
      return null;
    }
  },
  removeItem(key: string): void {
    try {
      sessionStorage.removeItem(key);
    } catch {
      // Ignore
    }
  },
  clear(): void {
    try {
      for (let i = sessionStorage.length - 1; i >= 0; i--) {
        const k = sessionStorage.key(i);
        if (k && k.startsWith("CognitoIdentityServiceProvider")) {
          sessionStorage.removeItem(k);
        }
      }
    } catch {
      // Ignore
    }
  },
};

export interface MappedAuthError {
  message: string;
  code?: string;
  isNotConfirmed?: boolean;
}

export function mapCognitoError(err: unknown): MappedAuthError {
  if (!err) {
    return { message: "An unexpected error occurred. Please try again." };
  }
  let code = "";
  let rawMsg = "";
  if (typeof err === "object" && err !== null) {
    if ("code" in err && typeof err.code === "string") {
      code = err.code;
    } else if ("name" in err && typeof err.name === "string") {
      code = err.name;
    }
    if ("message" in err && typeof err.message === "string") {
      rawMsg = err.message;
    }
  } else if (typeof err === "string") {
    rawMsg = err;
  }
  // Wrong email or password (no hint whether the account exists)
  if (
    code === "UserNotFoundException" ||
    code === "NotAuthorizedException" ||
    rawMsg.includes("Incorrect username or password")
  ) {
    return {
      message: "Incorrect email or password.",
      code: "INCORRECT_CREDENTIALS",
    };
  }

  // Account not verified (offer verify step)
  if (code === "UserNotConfirmedException" || rawMsg.includes("User is not confirmed")) {
    return {
      message: "Your account is not verified yet. Please check your email for the verification code.",
      code: "USER_NOT_CONFIRMED",
      isNotConfirmed: true,
    };
  }

  // Code wrong or expired
  if (
    code === "CodeMismatchException" ||
    code === "ExpiredCodeException" ||
    rawMsg.includes("Invalid verification code")
  ) {
    return {
      message: "The verification code is incorrect or has expired. Please check the code or request a new one.",
      code: "INVALID_CODE",
    };
  }

  // Too many attempts
  if (
    code === "LimitExceededException" ||
    code === "TooManyRequestsException" ||
    rawMsg.includes("Attempt limit exceeded")
  ) {
    return {
      message: "Too many attempts. Please wait a few moments before trying again.",
      code: "TOO_MANY_ATTEMPTS",
    };
  }

  // Password policy violation
  if (code === "InvalidPasswordException" || rawMsg.includes("Password does not conform")) {
    return {
      message:
        "Password does not meet the security policy (minimum 10 characters, including uppercase, lowercase, and numbers).",
      code: "INVALID_PASSWORD",
    };
  }

  // Username exists
  if (code === "UsernameExistsException") {
    return {
      message: "An account with this email already exists.",
      code: "USERNAME_EXISTS",
    };
  }

  // Network / connection error
  if (
    code === "NetworkError" ||
    rawMsg.toLowerCase().includes("network") ||
    rawMsg.toLowerCase().includes("failed to fetch") ||
    rawMsg.toLowerCase().includes("connection")
  ) {
    return {
      message: "Unable to reach the authentication service. Please check your network connection.",
      code: "NETWORK_ERROR",
    };
  }

  return {
    message: rawMsg && !rawMsg.includes("Exception") ? rawMsg : "Authentication request failed. Please try again.",
    code,
  };
}

export function getCognitoUserPool(cfg: AuthConfig): CognitoUserPool {
  return new CognitoUserPool({
    UserPoolId: cfg.user_pool_id,
    ClientId: cfg.client_id,
    Storage: sessionCognitoStorage,
  });
}

export interface CognitoTokensResult {
  idToken: string;
  accessToken: string;
  expiresInSec: number;
}

export function cognitoSignIn(
  cfg: AuthConfig,
  email: string,
  pass: string
): Promise<CognitoTokensResult> {
  return new Promise((resolve, reject) => {
    const pool = getCognitoUserPool(cfg);
    const cognitoUser = new CognitoUser({
      Username: email.trim().toLowerCase(),
      Pool: pool,
      Storage: sessionCognitoStorage,
    });
    const authDetails = new AuthenticationDetails({
      Username: email.trim().toLowerCase(),
      Password: pass,
    });

    cognitoUser.authenticateUser(authDetails, {
      onSuccess(session) {
        const idToken = session.getIdToken().getJwtToken();
        const accessToken = session.getAccessToken().getJwtToken();
        const exp = session.getIdToken().getExpiration(); // epoch seconds
        const now = Math.floor(Date.now() / 1000);
        const expiresInSec = Math.max(exp - now, 3600);
        resolve({ idToken, accessToken, expiresInSec });
      },
      onFailure(err) {
        reject(mapCognitoError(err));
      },
      newPasswordRequired() {
        reject({
          message: "A new password is required for this account.",
          code: "NEW_PASSWORD_REQUIRED",
        });
      },
    });
  });
}

export function cognitoSignUp(
  cfg: AuthConfig,
  email: string,
  pass: string
): Promise<{ userConfirmed: boolean; userSub: string }> {
  return new Promise((resolve, reject) => {
    const pool = getCognitoUserPool(cfg);
    const normalizedEmail = email.trim().toLowerCase();
    const attributeList = [
      new CognitoUserAttribute({
        Name: "email",
        Value: normalizedEmail,
      }),
    ];

    pool.signUp(
      normalizedEmail,
      pass,
      attributeList,
      [],
      (err, result) => {
        if (err || !result) {
          reject(mapCognitoError(err));
          return;
        }
        resolve({
          userConfirmed: result.userConfirmed,
          userSub: result.userSub,
        });
      }
    );
  });
}

export function cognitoConfirmSignUp(
  cfg: AuthConfig,
  email: string,
  code: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    const pool = getCognitoUserPool(cfg);
    const cognitoUser = new CognitoUser({
      Username: email.trim().toLowerCase(),
      Pool: pool,
      Storage: sessionCognitoStorage,
    });

    cognitoUser.confirmRegistration(code.trim(), true, (err) => {
      if (err) {
        reject(mapCognitoError(err));
        return;
      }
      resolve();
    });
  });
}

export function cognitoResendCode(
  cfg: AuthConfig,
  email: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    const pool = getCognitoUserPool(cfg);
    const cognitoUser = new CognitoUser({
      Username: email.trim().toLowerCase(),
      Pool: pool,
      Storage: sessionCognitoStorage,
    });

    cognitoUser.resendConfirmationCode((err) => {
      if (err) {
        reject(mapCognitoError(err));
        return;
      }
      resolve();
    });
  });
}

export function cognitoForgotPassword(
  cfg: AuthConfig,
  email: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    const pool = getCognitoUserPool(cfg);
    const cognitoUser = new CognitoUser({
      Username: email.trim().toLowerCase(),
      Pool: pool,
      Storage: sessionCognitoStorage,
    });

    cognitoUser.forgotPassword({
      onSuccess() {
        resolve();
      },
      onFailure(err) {
        reject(mapCognitoError(err));
      },
      inputVerificationCode() {
        resolve();
      },
    });
  });
}

export function cognitoConfirmPassword(
  cfg: AuthConfig,
  email: string,
  code: string,
  newPass: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    const pool = getCognitoUserPool(cfg);
    const cognitoUser = new CognitoUser({
      Username: email.trim().toLowerCase(),
      Pool: pool,
      Storage: sessionCognitoStorage,
    });

    cognitoUser.confirmPassword(code.trim(), newPass, {
      onSuccess() {
        resolve();
      },
      onFailure(err) {
        reject(mapCognitoError(err));
      },
    });
  });
}

export function cognitoSignOut(cfg: AuthConfig | null): void {
  if (!cfg) return;
  try {
    const pool = getCognitoUserPool(cfg);
    const user = pool.getCurrentUser();
    if (user) {
      user.signOut();
    }
  } catch {
    // Ignore sign-out cleanup issues
  }
  sessionCognitoStorage.clear();
}
