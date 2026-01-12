# Authentication Setup Guide

## Overview

**Users can simply login with Google and start using immediately** - no manual access setup required!

The system automatically creates user profiles on first login.

## How It Works

1. **User clicks "Sign in with Google"** → Supabase handles Google OAuth
2. **After successful authentication** → User is redirected to `/chat`
3. **Backend auto-creates user profile** → On first API call, user record is automatically created in `public.users` table

## One-Time Supabase Setup (Required)

### Step 1: Enable Google OAuth Provider

1. Go to **Supabase Dashboard** → **Authentication** → **Providers**
2. Find **Google** in the list
3. Click **Enable**
4. You'll need:
   - **Client ID** (from Google Cloud Console)
   - **Client Secret** (from Google Cloud Console)

### Step 2: Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs: 
   ```
   https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback
   ```
   (Replace `YOUR_PROJECT_REF` with your Supabase project reference)
7. Copy the **Client ID** and **Client Secret**

### Step 3: Configure in Supabase

1. In Supabase → Authentication → Providers → Google
2. Paste **Client ID** and **Client Secret**
3. Click **Save**

### Step 4: Verify Database Schema

Make sure you've run the database setup:

```sql
-- Run this in Supabase SQL Editor
-- File: backend/database/reset_and_recreate.sql
```

This creates the `users` table that supports auto-creation.

## User Flow

### First-Time User

1. User visits `/login`
2. Clicks "Sign in with Google"
3. Authenticates with Google
4. Redirected to `/chat`
5. **Backend automatically creates user profile** (no manual step needed)
6. User can immediately start chatting and uploading documents

### Returning User

1. User visits `/login` (or any protected page)
2. If session exists → Redirected to `/chat`
3. If no session → Shows login page
4. Clicks "Sign in with Google"
5. Authenticates → Redirected to `/chat`
6. User profile already exists, so no creation needed

## No Manual Access Required

✅ **No need to manually create users in Supabase**
✅ **No need to manually grant access**
✅ **No need to add users to any allowlist**
✅ **Any user who can authenticate with Google can use the system**

## Troubleshooting

### Issue: "Invalid OAuth credentials"

**Solution**: Check that Google OAuth is properly configured in Supabase with correct Client ID and Secret.

### Issue: "User not found" error

**Solution**: 
1. Check that database schema is set up (run `reset_and_recreate.sql`)
2. Check that `users` table exists
3. Check backend logs for auto-creation errors

### Issue: Redirect not working

**Solution**: 
1. Verify redirect URL in Supabase matches your frontend URL
2. Check that `/auth/callback` route exists in frontend
3. Verify CORS settings allow your frontend domain

## Security Notes

- **Single User System**: All authenticated users can access all documents
- **No RBAC**: No role-based access control (simplified for single user)
- **Auto-Creation**: User profiles are created automatically on first login
- **Session Management**: Supabase handles JWT tokens and session management

## Testing

1. **Test First-Time Login**:
   - Use a Google account that hasn't logged in before
   - Should auto-create user profile
   - Check `public.users` table in Supabase to verify

2. **Test Returning User**:
   - Log out
   - Log back in with same Google account
   - Should use existing profile (no new creation)

3. **Test Auto-Creation**:
   - Check backend logs for "Auto-creating user profile" message
   - Verify user appears in `public.users` table after first login

