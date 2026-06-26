import { Configuration, RedirectRequest } from "@azure/msal-browser";

/**
 * Configuración de MSAL Browser v5 para autenticación con Azure AD
 * @see https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig: Configuration = {
    auth: {
        clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "5eeff209-e05e-4fd5-af00-d911b6ca43a9",
        authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID || "8972f9d0-e562-41bc-9ff5-4b09d7bb0688"}`,
        redirectUri: import.meta.env.VITE_AZURE_REDIRECT_URI || `${window.location.origin}/azure-callback`,
        postLogoutRedirectUri: window.location.origin,
    },
    cache: {
        cacheLocation: "sessionStorage",
    },
    system: {
        loggerOptions: {
            loggerCallback: (level, message, containsPii) => {
                if (containsPii) {
                    return;
                }
                switch (level) {
                    case 0: // LogLevel.Error
                        console.error(message);
                        return;
                    case 1: // LogLevel.Warning
                        console.warn(message);
                        return;
                    case 2: // LogLevel.Info
                        console.info(message);
                        return;
                    case 3: // LogLevel.Verbose
                        console.debug(message);
                        return;
                }
            },
            logLevel: 2, // Info level
        },
        popupBridgeTimeout: 120000, // 2 minutos para popups
        redirectNavigationTimeout: 60000, // 1 minuto para redirects
    },
};

/**
 * Configuración de scopes para la solicitud de login
 * - User.Read: Permiso básico para leer el perfil del usuario
 * - openid: Requerido para OpenID Connect
 * - profile: Información del perfil básico
 * - email: Dirección de email del usuario
 */
export const loginRequest: RedirectRequest = {
    scopes: ["User.Read", "openid", "profile", "email"],
    prompt: "select_account", // Permite al usuario seleccionar la cuenta
};

