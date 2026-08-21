# Login 500 Error Fix - Production Deployment

## Problem
When logging in on Render with `superadmin@electwin.com`, the `/api/v1/auth/login/request-otp` endpoint returns:
```json
{
  "success": false,
  "error": {
    "code": "DATABASE_ERROR",
    "message": "A database error occurred during request execution."
  }
}
```

## Root Cause
The super admin user (`superadmin@electwin.com`) does not exist in the live Neon database. The app's bootstrap function attempts to create it on startup, but this may fail silently or the data may not have been committed.

## Verification (How to Check if You Have This Issue)
Query your Neon database:
```sql
SELECT email, first_name, last_name, is_superuser FROM users WHERE email = 'superadmin@electwin.com';
```

If no rows are returned, you have this issue.

## Solution: Re-seed Super Admin on Neon

### Option 1: Via Render Shell (Recommended)
Render provides a shell where you can run commands on your deployed service.

1. Go to your Render service dashboard
2. Click "Shell" tab
3. Run:
   ```bash
   python manual_seed.py
   ```
4. Expected output:
   ```
   ✓ Super admin already exists: superadmin@electwin.com
   # OR if not seeded
   ✓ Super admin created: superadmin@electwin.com (Super Administrator)
   ```

### Option 2: Via Database Direct Query (Manual)
1. Connect to your Neon database using pgAdmin or SQL client
2. Run this SQL:
   ```sql
   -- First, create roles if they don't exist
   INSERT INTO roles (id, organization_id, name, code, is_system, created_at, updated_at)
   SELECT 
     'role-super-admin-' || gen_random_uuid()::text,
     NULL,
     'Super Admin',
     'SUPER_ADMIN',
     true,
     NOW(),
     NOW()
   WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code = 'SUPER_ADMIN' AND is_system = true);

   -- Create super admin user (use correct password hash)
   INSERT INTO users (id, email, phone, password_hash, first_name, last_name, 
                      is_active, is_verified, is_superuser, created_at, updated_at)
   VALUES (
     'user-super-admin-' || gen_random_uuid()::text,
     'superadmin@electwin.com',
     '+91 98290 14285',
     '$2b$12$...',  -- Use the hash from `bcrypt.hashpw("SuperSecureAdminPassword123!".encode(), salt)`
     'Super',
     'Administrator',
     true,
     true,
     true,
     NOW(),
     NOW()
   )
   ON CONFLICT (email) DO NOTHING;
   ```
   > Note: Getting the correct bcrypt hash is complex. **Use Option 1 instead.**

### Option 3: Redeploy from Updated Code
Push a small change to trigger a Render redeploy:
1. Commit: `git commit --allow-empty -m "Trigger redeployment for seed verification"`
2. Push: `git push origin main`
3. Render will redeploy, running the app startup code which seeds the data

## After Fix: Verify Login Works
1. Go to your deployed frontend: `https://votingmanagment-front-end.vercel.app/login`
2. Enter:
   - Email: `superadmin@electwin.com`
   - Password: `SuperSecureAdminPassword123!`
3. Click "Request OTP"
4. Should see success message and OTP input field (not 500 error)

## Prevention for Future
Ensure the manual_seed.py script is included in the repo and documented so you can re-seed if needed:
```bash
# On Render shell:
python manual_seed.py
```

## Monitoring
Add this health check query to your monitoring:
```sql
SELECT COUNT(*) as super_admin_count FROM users WHERE email = 'superadmin@electwin.com' AND is_superuser = true;
```
Should always return 1. If 0, re-run the seed.
