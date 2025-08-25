/**
 * Keycloak context for managing authentication state across the app.
 */
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import keycloakService, { KeycloakUser } from '../services/keycloakService';

interface KeycloakContextType {
  user: KeycloakUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getToken: () => string | null;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
  hasGroup: (group: string) => boolean;
  updateToken: () => Promise<boolean>;
}

const KeycloakContext = createContext<KeycloakContextType | undefined>(undefined);

interface KeycloakProviderProps {
  children: ReactNode;
}

export const KeycloakProvider: React.FC<KeycloakProviderProps> = ({ children }) => {
  const [user, setUser] = useState<KeycloakUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initKeycloak = async () => {
      try {
        setIsLoading(true);
        const authenticated = await keycloakService.init();
        
        if (authenticated) {
          const userInfo = keycloakService.getUser();
          setUser(userInfo);
          setIsAuthenticated(true);
        } else {
          setUser(null);
          setIsAuthenticated(false);
        }

        // Set up event listeners
        keycloakService.onAuthSuccess(() => {
          const userInfo = keycloakService.getUser();
          setUser(userInfo);
          setIsAuthenticated(true);
        });

        keycloakService.onAuthError((error: any) => {
          console.error('Keycloak auth error:', error);
          setUser(null);
          setIsAuthenticated(false);
        });

        keycloakService.onAuthRefreshSuccess(() => {
          const userInfo = keycloakService.getUser();
          setUser(userInfo);
        });

        keycloakService.onAuthRefreshError(() => {
          console.error('Token refresh failed');
          setUser(null);
          setIsAuthenticated(false);
        });

        keycloakService.onAuthLogout(() => {
          setUser(null);
          setIsAuthenticated(false);
        });

        keycloakService.onTokenExpired(() => {
          console.log('Token expired, attempting refresh...');
          keycloakService.updateToken().catch(() => {
            setUser(null);
            setIsAuthenticated(false);
          });
        });

      } catch (error) {
        console.error('Failed to initialize Keycloak:', error);
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    initKeycloak();
  }, []);

  const login = async () => {
    try {
      await keycloakService.login();
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await keycloakService.logout();
      setUser(null);
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Logout failed:', error);
      throw error;
    }
  };

  const getToken = () => {
    return keycloakService.getToken() || null;
  };

  const hasRole = (role: string) => {
    return keycloakService.hasRole(role);
  };

  const hasAnyRole = (roles: string[]) => {
    return keycloakService.hasAnyRole(roles);
  };

  const hasGroup = (group: string) => {
    return keycloakService.hasGroup(group);
  };

  const updateToken = async () => {
    return await keycloakService.updateToken();
  };

  const contextValue: KeycloakContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    getToken,
    hasRole,
    hasAnyRole,
    hasGroup,
    updateToken,
  };

  return (
    <KeycloakContext.Provider value={contextValue}>
      {children}
    </KeycloakContext.Provider>
  );
};

export const useKeycloak = (): KeycloakContextType => {
  const context = useContext(KeycloakContext);
  if (context === undefined) {
    throw new Error('useKeycloak must be used within a KeycloakProvider');
  }
  return context;
};

export default KeycloakContext;
