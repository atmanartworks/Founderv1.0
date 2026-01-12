"use client";

export const dynamic = "force-dynamic";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function AuthCallbackPage() {
    const router = useRouter();

    useEffect(() => {
        const handleCallback = async () => {
            const { error } = await supabase.auth.getSession();
            if (!error) {
                router.push("/chat");
            }
        };

        // In Implicit/PKCE flow (standard for supabase-js), the library handles parsing the hash.
        // However, usually we redirect to a page that just lets the library do its work.
        // If we use `signInWithOAuth` with `redirectTo`, we come back here.
        // supabase.auth.onAuthStateChange handles the rest usually.
        // Let's just wait a tick and redirect.
        // Or better:

        supabase.auth.onAuthStateChange((event: string, session: any) => {
            if (event === 'SIGNED_IN') {
                // Store token for our manual API calls helper
                if (session && session.access_token) {
                    localStorage.setItem("supabase_token", session.access_token);
                }
                router.push("/chat");
            }
        });

    }, [router]);

    return (
        <div className="flex h-screen w-full items-center justify-center">
            <p>Authenticating...</p>
        </div>
    );
}
