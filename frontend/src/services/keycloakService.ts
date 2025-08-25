import Keycloak from 'keycloak-js';

export interface KeycloakUser {
  sub: string;
  email?: string;
  preferred_username?: string;
  name?: string;
  given_name?: string;
  family_name?: string;
  email_verified?: boolean;
  realm_access?: any;
  resource_access?: any;
}

class KeycloakService {
  private keycloak: Keycloak | null = null;
  private initialized = false;

  async init(): Promise<boolean> {
    if (this.initialized) {
      return true;
    }

    try {
      const response = await fetch('/api/auth/config');
      const config = await response.json();

      if (!config.server_url || !config.realm || !config.client_id) {
        console.error('Keycloak configuration missing from backend');
        return false;
      }

      this.keycloak = new Keycloak({
        url: config.server_url,
        realm: config.realm,
        clientId: config.client_id,
      });

      const authenticated = await this.keycloak.init({
        onLoad: 'check-sso',
        silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
        checkLoginIframe: false,
      });

      this.initialized = true;
      return authenticated;
    } catch (error) {
      console.error('Failed to initialize Keycloak:', error);
      return false;
    }
  }

  async login(): Promise<void> {
    if (!this.keycloak) {
      throw new Error('Keycloak not initialized');
    }
    await this.keycloak.login();
  }

  async logout(): Promise<void> {
    if (!this.keycloak) {
      throw new Error('Keycloak not initialized');
    }
    await this.keycloak.logout();
  }

  async register(): Promise<void> {
    if (!this.keycloak) {
      throw new Error('Keycloak not initialized');
    }
    await this.keycloak.register();
  }

  getToken(): string | undefined {
    return this.keycloak?.token;
  }

  getRefreshToken(): string | undefined {
    return this.keycloak?.refreshToken;
  }

  isAuthenticated(): boolean {
    return this.keycloak?.authenticated || false;
  }

  getUser(): KeycloakUser | null {
    if (!this.keycloak?.tokenParsed) {
      return null;
    }

    const token = this.keycloak.tokenParsed as any;
    return {
      sub: token.sub,
      email: token.email,
      preferred_username: token.preferred_username,
      name: token.name,
      given_name: token.given_name,
      family_name: token.family_name,
      email_verified: token.email_verified,
      realm_access: token.realm_access,
      resource_access: token.resource_access,
    };
  }

  async updateToken(): Promise<boolean> {
    if (!this.keycloak) {
      return false;
    }

    try {
      const refreshed = await this.keycloak.updateToken(30);
      return refreshed;
    } catch (error) {
      console.error('Failed to refresh token:', error);
      return false;
    }
  }

  onAuthSuccess(callback: () => void): void {
    if (this.keycloak) {
      this.keycloak.onAuthSuccess = callback;
    }
  }

  onAuthError(callback: (error: any) => void): void {
    if (this.keycloak) {
      this.keycloak.onAuthError = callback;
    }
  }

  onAuthRefreshSuccess(callback: () => void): void {
    if (this.keycloak) {
      this.keycloak.onAuthRefreshSuccess = callback;
    }
  }

  onAuthRefreshError(callback: () => void): void {
    if (this.keycloak) {
      this.keycloak.onAuthRefreshError = callback;
    }
  }

  onTokenExpired(callback: () => void): void {
    if (this.keycloak) {
      this.keycloak.onTokenExpired = callback;
    }
  }

  onAuthLogout(callback: () => void): void {
    if (this.keycloak) {
      this.keycloak.onAuthLogout = callback;
    }
  }

  hasRole(role: string): boolean {
    if (!this.keycloak?.tokenParsed) {
      return false;
    }
    
    const token = this.keycloak.tokenParsed as any;
    const realmRoles = token.realm_access?.roles || [];
    const clientRoles = Object.values(token.resource_access || {}).flatMap((client: any) => client.roles || []);
    
    return [...realmRoles, ...clientRoles].includes(role);
  }

  hasAnyRole(roles: string[]): boolean {
    return roles.some(role => this.hasRole(role));
  }

  hasGroup(group: string): boolean {
    if (!this.keycloak?.tokenParsed) {
      return false;
    }
    
    const token = this.keycloak.tokenParsed as any;
    const groups = token.groups || [];
    return groups.includes(group);
  }
}

const keycloakService = new KeycloakService();
export default keycloakService;
export { keycloakService };
