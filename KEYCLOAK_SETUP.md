# Keycloak Setup Guide

This guide will help you configure Keycloak for the AI Embedder application.

## Prerequisites

- Docker containers are running (including Keycloak on port 8080)
- Access to Keycloak Admin Console

## Step 1: Access Keycloak Admin Console

1. Open your browser and go to: http://localhost:8080
2. Click on "Administration Console"
3. Login with:
   - **Username**: `admin`
   - **Password**: `admin`

## Step 2: Create a New Realm

1. In the top-left corner, click on the dropdown that says "Master"
2. Click "Create Realm"
3. Fill in the realm details:
   - **Realm name**: `embedder`
   - **Enabled**: ON (checked)
4. Click "Create"

## Step 3: Create a Client

1. In the left sidebar, click on "Clients"
2. Click "Create client"
3. Fill in the client details:
   - **Client type**: OpenID Connect
   - **Client ID**: `embedder-client`
   - Click "Next"

4. Configure client authentication:
   - **Client authentication**: ON (enabled)
   - **Authorization**: OFF (disabled)
   - **Authentication flow**: 
     - ✅ Standard flow
     - ✅ Direct access grants
     - ❌ Implicit flow
     - ❌ Service accounts roles
   - Click "Next"

5. Configure login settings:
   - **Root URL**: `http://localhost:3333`
   - **Home URL**: `http://localhost:3333`
   - **Valid redirect URIs**: 
     - `http://localhost:3333/*`
   - **Valid post logout redirect URIs**: 
     - `http://localhost:3333/*`
   - **Web origins**: `http://localhost:3333`
   - Click "Save"

## Step 4: Get Client Secret

1. Go to the "Credentials" tab of your client
2. Copy the **Client Secret** value
3. Update your environment variables:
   ```bash
   KEYCLOAK_CLIENT_SECRET=your_copied_client_secret_here
   ```

## Step 5: Configure Realm Settings (Optional)

1. Go to "Realm settings" in the left sidebar
2. In the "Login" tab, you can configure:
   - **User registration**: ON (to allow new users to register)
   - **Forgot password**: ON (to enable password reset)
   - **Remember me**: ON (for better UX)
   - **Login with email**: ON (allow login with email instead of username)

## Step 6: Create a Test User (Optional)

1. In the left sidebar, click on "Users"
2. Click "Create new user"
3. Fill in user details:
   - **Username**: `testuser`
   - **Email**: `test@example.com`
   - **First name**: `Test`
   - **Last name**: `User`
   - **Email verified**: ON
   - **Enabled**: ON
4. Click "Create"
5. Go to the "Credentials" tab
6. Click "Set password"
7. Enter a password and set "Temporary" to OFF
8. Click "Save"

## Step 7: Test the Configuration

1. Restart your application containers:
   ```bash
   docker-compose restart backend frontend
   ```

2. Open your application: http://localhost:3333
3. Try to access a protected page - you should be redirected to Keycloak login
4. Login with your test user credentials
5. You should be redirected back to your application

## Environment Variables Summary

Make sure your `docker-compose.yml` or `.env` file has these variables set:

```env
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_REALM=embedder
KEYCLOAK_CLIENT_ID=embedder-client
KEYCLOAK_CLIENT_SECRET=your_client_secret_from_step_4
KEYCLOAK_ADMIN_CLIENT_ID=admin-cli
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin
```

## Troubleshooting

### Common Issues:

1. **"Invalid redirect URI"**: 
   - Check that your redirect URIs in Keycloak match your frontend URL
   - Make sure to include `/*` at the end of the redirect URI

2. **"Client not found"**:
   - Verify the client ID matches exactly: `embedder-client`
   - Make sure you're in the correct realm: `embedder`

3. **Connection refused**:
   - Check that Keycloak is running: `docker-compose ps`
   - Verify the Keycloak URL is accessible: http://localhost:8080

4. **CORS errors**:
   - Make sure "Web origins" is set to `http://localhost:3333` in the client settings

### Logs:

Check application logs for detailed error messages:
```bash
docker-compose logs backend
docker-compose logs frontend
docker-compose logs keycloak
```

## Next Steps

Once Keycloak is configured:
1. Your application will use Keycloak for authentication
2. Users can register, login, and logout through Keycloak
3. JWT tokens will be automatically managed
4. User sessions will persist across browser refreshes

The application will automatically redirect users to Keycloak for authentication when they try to access protected resources.
