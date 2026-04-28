/**
 * Utilidades de firma digital usando Web Crypto API (SubtleCrypto).
 *
 * Algoritmo: ECDSA con curva P-256 y hash SHA-256.
 *
 * Modelo SAT:
 *   - El backend genera el par de claves y entrega:
 *     * .cer — certificado público X.509 PEM
 *     * .key — clave privada cifrada (PBKDF2 + AES-256-GCM, formato custom)
 *   - Para firmar: el usuario SUBE su .key + contraseña → se descifra
 *     en memoria → se firma → la clave se descarta de memoria
 *
 * La clave privada SOLO existe en el archivo .key cifrado.
 * No se almacena en IndexedDB ni en ningún otro lugar del navegador.
 */

// PBKDF2 parameters — DEBEN coincidir con signing_service.py
const PBKDF2_ITERATIONS = 600000;
const SALT_LENGTH = 16;
const IV_LENGTH = 12;

// ──────────────────────────────────────────────────────────────────
//  Descarga de archivos
// ──────────────────────────────────────────────────────────────────

/**
 * Descarga un string como archivo.
 */
export function downloadAsFile(content, filename, mimeType = "application/x-pem-file") {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ──────────────────────────────────────────────────────────────────
//  Descifrado de clave privada (.key)
// ──────────────────────────────────────────────────────────────────

/**
 * Descifra un archivo .key y retorna el CryptoKey privado.
 * Compatible con formato generado por el backend (PBKDF2 + AES-256-GCM).
 *
 * @param {string} keyFileContent - Contenido del archivo .key
 * @param {string} password - Contraseña de la clave privada
 * @returns {CryptoKey} Clave privada ECDSA P-256 para firmar
 */
export async function decryptKeyFile(keyFileContent, password) {
  const b64 = keyFileContent
    .replace(/-----BEGIN CASA MONARCA ENCRYPTED KEY-----/, "")
    .replace(/-----END CASA MONARCA ENCRYPTED KEY-----/, "")
    .replace(/\s/g, "");

  let combined;
  try {
    combined = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  } catch {
    throw new Error("El archivo no tiene un formato válido.");
  }

  if (combined.length < SALT_LENGTH + IV_LENGTH + 1) {
    throw new Error("El archivo de clave privada está corrupto.");
  }

  const salt = combined.slice(0, SALT_LENGTH);
  const iv = combined.slice(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
  const ciphertext = combined.slice(SALT_LENGTH + IV_LENGTH);

  const passwordKey = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  const aesKey = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    passwordKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"]
  );

  let pkcs8Bytes;
  try {
    const decrypted = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv },
      aesKey,
      ciphertext
    );
    pkcs8Bytes = new Uint8Array(decrypted);
  } catch {
    throw new Error("Contraseña incorrecta o archivo dañado.");
  }

  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    pkcs8Bytes,
    { name: "ECDSA", namedCurve: "P-256" },
    false, // No exportable — solo para firmar en este momento
    ["sign"]
  );

  return privateKey;
}

// ──────────────────────────────────────────────────────────────────
//  Firma de contenido (con archivo .key + contraseña)
// ──────────────────────────────────────────────────────────────────

/**
 * Firma un contenido usando un archivo .key cifrado + contraseña.
 *
 * La clave privada se descifra en memoria, se usa para firmar,
 * y se descarta inmediatamente. No se guarda en ningún lado.
 *
 * @param {string} contentString - Contenido canónico a firmar
 * @param {string} keyFileContent - Contenido del archivo .key cifrado
 * @param {string} password - Contraseña del archivo
 * @returns {{ contentHash: string, signatureB64: string }}
 */
export async function signContent(contentString, keyFileContent, password) {
  // 1. Descifrar la clave privada del archivo .key
  const privateKey = await decryptKeyFile(keyFileContent, password);

  // 2. Firmar
  const encoder = new TextEncoder();
  const data = encoder.encode(contentString);

  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const sigBuffer = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    privateKey,
    data
  );

  const contentHash = bufferToHex(hashBuffer);
  const signatureB64 = bufferToBase64(sigBuffer);

  // La clave privada queda fuera de scope y será recolectada por GC
  return { contentHash, signatureB64 };
}

// ──────────────────────────────────────────────────────────────────
//  Helpers
// ──────────────────────────────────────────────────────────────────

function bufferToHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function bufferToBase64(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}

/**
 * Crea el contenido canónico de un registro para firmarlo.
 */
export function buildCanonicalContent(resourceType, resourceId, extraData = {}) {
  const payload = {
    resource_type: resourceType,
    resource_id: resourceId,
    ...extraData,
  };
  return JSON.stringify(payload, Object.keys(payload).sort());
}
