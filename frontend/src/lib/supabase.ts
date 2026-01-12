import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Create a singleton client. 
// At build time, if keys are missing, we export a proxy or empty object to prevent crashing.
export const supabase = (SUPABASE_URL && SUPABASE_ANON_KEY)
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    : new Proxy({} as any, {
        get: (target, prop) => {
            if (prop === 'auth') return { getSession: async () => ({ data: { session: null } }), onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => { } } } }) };
            return () => ({ from: () => ({ select: () => ({ execute: async () => ({ data: [], error: null }) }) }) });
        }
    });

