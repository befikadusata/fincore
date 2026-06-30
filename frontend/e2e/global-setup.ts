import { request } from '@playwright/test';
import fs from 'fs';
import path from 'path';

function resolveApiUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  // Read HOST_DJANGO_PORT from the root .env so the port stays in sync with docker-compose
  try {
    const rootEnv = fs.readFileSync(path.join(__dirname, '..', '..', '.env'), 'utf-8');
    const match = rootEnv.match(/^HOST_DJANGO_PORT=(\d+)/m);
    if (match) return `http://127.0.0.1:${match[1]}`;
  } catch { /* ignore */ }
  return 'http://127.0.0.1:8000';
}

const API_URL = resolveApiUrl();
const AUTH_DIR = path.join(__dirname, '.auth');
const USER_FILE = path.join(AUTH_DIR, 'user.json');
const DATA_FILE = path.join(AUTH_DIR, 'test-data.json');

const TEST_USER = {
  first_name: 'E2E',
  last_name: 'Test',
  email: 'e2e@test.fincore',
  password: 'TestPass123!',
};

type Tenant = { id: string; name: string; slug: string; status: string };
type Product = { id: string; name: string };

export default async function globalSetup() {
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  const api = await request.newContext({ baseURL: API_URL });

  // Register — ignore 400 if user already exists
  const regRes = await api.post('/api/v1/auth/register/', { data: TEST_USER });
  if (!regRes.ok() && regRes.status() !== 400) {
    throw new Error(`Registration failed ${regRes.status()}: ${await regRes.text()}`);
  }

  // Login
  const tokenRes = await api.post('/api/v1/auth/token/', {
    data: { email: TEST_USER.email, password: TEST_USER.password },
  });
  if (!tokenRes.ok()) throw new Error(`Login failed: ${await tokenRes.text()}`);
  const { access, refresh } = (await tokenRes.json()) as { access: string; refresh: string };

  // Get user + tenants
  const meRes = await api.get('/api/v1/auth/me/', {
    headers: { Authorization: `Bearer ${access}` },
  });
  if (!meRes.ok()) throw new Error(`/me failed: ${await meRes.text()}`);
  const { user, tenants: initialTenants } = (await meRes.json()) as {
    user: Record<string, unknown>;
    tenants: Tenant[];
  };

  // If no tenant exists yet, create one
  let tenants = initialTenants;
  if (tenants.length === 0) {
    const createTenantRes = await api.post('/api/v1/tenants/', {
      headers: { Authorization: `Bearer ${access}` },
      data: { name: 'E2E Org', slug: 'e2e-org' },
    });
    if (!createTenantRes.ok() && createTenantRes.status() !== 400) {
      throw new Error(`Create tenant failed: ${await createTenantRes.text()}`);
    }
    // Re-fetch /me to get updated tenants list
    const me2Res = await api.get('/api/v1/auth/me/', {
      headers: { Authorization: `Bearer ${access}` },
    });
    const me2 = (await me2Res.json()) as { user: Record<string, unknown>; tenants: Tenant[] };
    tenants = me2.tenants;
  }

  const activeTenant = tenants[0];
  if (!activeTenant) throw new Error('No tenant available after setup');

  // Create loan product — fall back to fetching existing if name taken
  const prodHeaders = {
    Authorization: `Bearer ${access}`,
    'X-Tenant-ID': activeTenant.id,
  };
  const PRODUCT_NAME = 'E2E Standard Loan';

  let loanProductId = '';
  const prodRes = await api.post('/api/v1/finance/loan-products/', {
    headers: prodHeaders,
    data: {
      name: PRODUCT_NAME,
      interest_type: 'flat',
      interest_rate: '10.00',
      min_term_months: 1,
      max_term_months: 60,
      min_amount: '1000.00',
      max_amount: '500000.00',
    },
  });

  if (prodRes.ok()) {
    loanProductId = ((await prodRes.json()) as Product).id;
  } else {
    const listRes = await api.get('/api/v1/finance/loan-products/', { headers: prodHeaders });
    const body = (await listRes.json()) as { results?: Product[] } | Product[];
    const products = Array.isArray(body) ? body : (body.results ?? []);
    loanProductId = products.find((p) => p.name === PRODUCT_NAME)?.id ?? '';
    if (!loanProductId) {
      throw new Error(`Loan product creation failed and no existing product found: ${await prodRes.text()}`);
    }
  }

  await api.dispose();

  // Write browser storage state directly — no browser launch needed
  const storageState = {
    cookies: [
      {
        name: 'access_token',
        value: access,
        domain: 'localhost',
        path: '/',
        expires: Math.floor(Date.now() / 1000) + 7 * 86400,
        httpOnly: false,
        secure: false,
        sameSite: 'Strict' as const,
      },
    ],
    origins: [
      {
        origin: 'http://localhost:3100',
        localStorage: [
          {
            name: 'fincore-auth',
            value: JSON.stringify({
              state: { user, accessToken: access, refreshToken: refresh },
              version: 0,
            }),
          },
          {
            name: 'fincore-tenant',
            value: JSON.stringify({
              state: { activeTenant, tenants },
              version: 0,
            }),
          },
        ],
      },
    ],
  };

  fs.writeFileSync(USER_FILE, JSON.stringify(storageState, null, 2));
  fs.writeFileSync(
    DATA_FILE,
    JSON.stringify(
      {
        email: TEST_USER.email,
        password: TEST_USER.password,
        tenantId: activeTenant.id,
        tenantName: activeTenant.name,
        loanProductId,
        loanProductName: PRODUCT_NAME,
      },
      null,
      2,
    ),
  );

  console.log(`[global-setup] tenant="${activeTenant.name}" product="${loanProductId}"`);
}
