import { SignJWT, jwtVerify } from "jose";

const COOKIE_NAME = "shopifysift_session";
const ALGO = "HS256";
const TTL_SECONDS = 60 * 60 * 24 * 7; // 7 days

function getSecret(): Uint8Array {
  const secret = process.env.SHOPIFYSIFT_SECRET;
  if (!secret || secret.length < 32) {
    throw new Error(
      "SHOPIFYSIFT_SECRET env var must be set to at least 32 characters",
    );
  }
  return new TextEncoder().encode(secret);
}

export async function createSessionToken(user: string): Promise<string> {
  return await new SignJWT({ user })
    .setProtectedHeader({ alg: ALGO })
    .setIssuedAt()
    .setExpirationTime(`${TTL_SECONDS}s`)
    .sign(getSecret());
}

export async function verifySessionToken(
  token: string,
): Promise<{ user: string } | null> {
  try {
    const { payload } = await jwtVerify(token, getSecret());
    if (typeof payload.user !== "string") return null;
    return { user: payload.user };
  } catch {
    return null;
  }
}

export function checkCredentials(user: string, pass: string): boolean {
  const expectedUser = process.env.SHOPIFYSIFT_USER ?? "admin";
  const expectedPass = process.env.SHOPIFYSIFT_PASS ?? "admin";
  return user === expectedUser && pass === expectedPass;
}

export const SESSION_COOKIE = COOKIE_NAME;
export const SESSION_TTL_SECONDS = TTL_SECONDS;
