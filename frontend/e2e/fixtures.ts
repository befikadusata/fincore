import { test as base, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

export { expect };

export interface TestData {
  email: string;
  password: string;
  tenantId: string;
  tenantName: string;
  loanProductId: string;
  loanProductName: string;
}

export function getTestData(): TestData {
  return JSON.parse(
    fs.readFileSync(path.join(__dirname, '.auth', 'test-data.json'), 'utf-8'),
  ) as TestData;
}

export const test = base;
