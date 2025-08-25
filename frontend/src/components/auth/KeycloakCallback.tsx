import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKeycloak } from '../../contexts/KeycloakContext';

const KeycloakCallback: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading } = useKeycloak();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        navigate('/');
      } else {
        navigate('/login');
      }
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Processing authentication...</p>
        </div>
      </div>
    );
  }

  return null;
};

export default KeycloakCallback;