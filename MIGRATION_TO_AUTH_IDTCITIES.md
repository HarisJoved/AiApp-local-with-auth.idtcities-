# Migration to auth.idtcities.com

This document outlines the changes made to migrate from the local Keycloak Docker container to the remote auth.idtcities.com Keycloak instance.

## Overview

The application has been migrated from using a local Keycloak container (version 23.0.0) running on localhost:8080 to using the remote auth.idtcities.com Keycloak instance (version 26.1.4).

## Changes Made

### 1. Frontend Updates

#### package.json
- Updated `keycloak-js` from version `^23.0.0` to `^26.1.4`
- Changed proxy from `http://localhost:8888` to `https://auth.idtcities.com`

#### Environment Files
- **frontend/.env**: Updated `REACT_APP_API_URL` from `http://localhost:8888` to `https://auth.idtcities.com`
- **frontend/.env.example**: Updated example API URL to `https://auth.idtcities.com`

### 2. Backend Updates

#### Environment Files
- **backend/.env**: Updated `KEYCLOAK_SERVER_URL` from `http://localhost:8080` to `https://auth.idtcities.com`
- **backend/.env.example**: Updated example Keycloak URL to `https://auth.idtcities.com`
- **backend/.env**: Added `https://auth.idtcities.com` to `CORS_ORIGINS`

#### Configuration Files
- **backend/app/config/settings.py**: Updated default Keycloak server URL and CORS origins

### 3. Docker Configuration

#### docker-compose.yml
- Removed `keycloak` service (no longer needed locally)
- Removed `postgres` service (was only used by Keycloak)
- Updated backend service to remove Keycloak dependency
- Updated environment variables to use remote Keycloak URL
- Updated CORS origins to include the new domain

## Key Benefits

1. **No Local Keycloak Management**: Eliminates the need to run and maintain a local Keycloak instance
2. **Latest Version**: Access to Keycloak 26.1.4 features and security updates
3. **Centralized Authentication**: Single authentication service for multiple applications
4. **Reduced Resource Usage**: Less local system resources consumed
5. **Simplified Deployment**: Fewer services to manage in local development

## Configuration Requirements

### Frontend
- Ensure your Keycloak client is properly configured in the auth.idtcities.com realm
- Verify the client ID and realm name match your configuration
- Check that CORS is properly configured for your frontend domain

### Backend
- Update your environment variables with the correct Keycloak configuration
- Ensure your client secret is correct for the remote instance
- Verify that the admin credentials have the necessary permissions

## Testing the Migration

1. **Frontend**: Start the frontend and verify authentication flows work
2. **Backend**: Start the backend and verify it can connect to the remote Keycloak
3. **Integration**: Test the complete authentication flow from frontend to backend

## Rollback Plan

If issues arise, you can temporarily revert by:
1. Restoring the original docker-compose.yml with local Keycloak services
2. Reverting environment files to localhost URLs
3. Downgrading keycloak-js to version 23.0.0

## Notes

- The migration maintains backward compatibility for local development
- All existing authentication logic remains the same
- Token validation and user management continue to work as before
- The application now uses HTTPS for all Keycloak communications
