// Get API URL - use network IP if on another device, otherwise use localhost
// Made as a function to avoid module-level execution in serverless environments
const getApiUrl = () => {
    if (typeof window === 'undefined') {
        // Server-side: use environment variable or default
        return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    }
    
    // Check if NEXT_PUBLIC_API_URL is set
    if (process.env.NEXT_PUBLIC_API_URL) {
        return process.env.NEXT_PUBLIC_API_URL;
    }
    
    // If accessing from another device, use the network IP
    // Otherwise use localhost
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return "http://localhost:8000/api/v1";
    } else {
        // Use the same hostname but port 8000 for backend
        return `http://192.168.3.3:8000/api/v1`;
    }
};

// Lazy getter to avoid module-level execution issues in serverless
export const getAPIUrl = () => getApiUrl();

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
    // Check window for localStorage to avoid SSR errors
    let token = typeof window !== 'undefined' ? localStorage.getItem("supabase_token") : null;

    // If no token, try to get fresh session from Supabase
    if (!token && typeof window !== 'undefined') {
        const { supabase } = await import('./supabase');
        const { data: { session } } = await supabase.auth.getSession();
        if (session && session.access_token) {
            token = session.access_token;
            localStorage.setItem("supabase_token", token);
        }
    }

    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...options.headers as Record<string, string>,
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${getAPIUrl()}${url}`, {
        ...options,
        headers,
    });

    if (!res.ok) {
        // If 401, try refreshing the token
        if (res.status === 401 && typeof window !== 'undefined') {
            const { supabase } = await import('./supabase');
            const { data: { session } } = await supabase.auth.getSession();
            if (session && session.access_token) {
                // Update token and retry once
                localStorage.setItem("supabase_token", session.access_token);
                headers["Authorization"] = `Bearer ${session.access_token}`;
                const retryRes = await fetch(`${getAPIUrl()}${url}`, {
                    ...options,
                    headers,
                });
                if (retryRes.ok) {
                    return retryRes.json();
                }
            } else {
                // No session - redirect to login
                window.location.href = '/login';
                throw new Error("Session expired. Please log in again.");
            }
        }
        
        const error = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || "API request failed");
    }

    return res.json();
}

export async function uploadFileWithAuth(url: string, file: File, folderId?: string) {
    const token = typeof window !== 'undefined' ? localStorage.getItem("supabase_token") : null;
    const formData = new FormData();
    formData.append("file", file);
    if (folderId) formData.append("folder_id", folderId);

    const headers: Record<string, string> = {};
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${getAPIUrl()}${url}`, {
        method: "POST",
        headers,
        body: formData,
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || "Upload failed");
    }

    return res.json();
}

export async function listDocuments() {
    return fetchWithAuth("/documents/");
}

export async function getDocumentUrl(storagePath: string): Promise<string> {
    // For Supabase Storage, construct public URL
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    if (!supabaseUrl) {
        throw new Error("NEXT_PUBLIC_SUPABASE_URL is not configured");
    }
    return `${supabaseUrl}/storage/v1/object/public/GPTv1/${storagePath}`;
}

export async function downloadDocument(storagePath: string, fileName: string) {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
        throw new Error("downloadDocument can only be called in the browser");
    }
    const url = await getDocumentUrl(storagePath);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

export async function deleteDocument(documentId: string) {
    return fetchWithAuth(`/documents/${documentId}`, {
        method: "DELETE",
    });
}

// Folder Management API
export async function listFolders(parentId?: string) {
    const url = parentId ? `/folders?parent_id=${parentId}` : "/folders/";
    return fetchWithAuth(url);
}

export async function getFolder(folderId: string) {
    return fetchWithAuth(`/folders/${folderId}`);
}

export async function createFolder(data: { name: string; parent_id?: string; allowed_roles?: string[]; allowed_users?: string[] }) {
    return fetchWithAuth("/folders/", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function updateFolder(folderId: string, data: { name?: string; parent_id?: string; allowed_roles?: string[]; allowed_users?: string[] }) {
    return fetchWithAuth(`/folders/${folderId}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
}

export async function deleteFolder(folderId: string) {
    return fetchWithAuth(`/folders/${folderId}`, {
        method: "DELETE",
    });
}

export async function getFolderTree() {
    return fetchWithAuth("/folders/tree/all");
}

export async function deleteConversation(conversationId: string) {
    return fetchWithAuth(`/chat/conversations/${conversationId}`, {
        method: "DELETE",
    });
}

export async function updateConversation(conversationId: string, title: string) {
    return fetchWithAuth(`/chat/conversations/${conversationId}`, {
        method: "PUT",
        body: JSON.stringify({ title }),
    });
}

export async function reprocessDocument(documentId: string) {
    return fetchWithAuth(`/documents/${documentId}/reprocess`, {
        method: "POST",
    });
}

export async function listFolderDocuments(folderId: string) {
    return fetchWithAuth(`/folders/${folderId}/documents`);
}

// Admin API
export async function listAllUsers() {
    return fetchWithAuth("/admin/users");
}

export async function createUser(data: { email: string; full_name?: string; role: string }) {
    return fetchWithAuth("/admin/users", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function updateUser(userId: string, data: { full_name?: string; role?: string }) {
    return fetchWithAuth(`/admin/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
    });
}

export async function deleteUser(userId: string) {
    return fetchWithAuth(`/admin/users/${userId}`, {
        method: "DELETE",
    });
}

export async function getAdminStats() {
    return fetchWithAuth("/admin/stats");
}

export async function listAllFolders() {
    return fetchWithAuth("/admin/folders");
}

export async function listAllDocuments() {
    return fetchWithAuth("/admin/documents");
}

// Analytics API
export async function getConversationLogs(params?: {
    user_id?: string;
    conversation_id?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
}) {
    const queryParams = new URLSearchParams();
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                queryParams.append(key, value.toString());
            }
        });
    }
    const url = `/analytics/conversation-logs${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return fetchWithAuth(url);
}

export async function getAnalytics(startDate?: string, endDate?: string) {
    const queryParams = new URLSearchParams();
    if (startDate) queryParams.append("start_date", startDate);
    if (endDate) queryParams.append("end_date", endDate);
    const url = `/analytics/analytics${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return fetchWithAuth(url);
}

// Document Versioning API
export async function getDocumentVersions(documentId: string) {
    return fetchWithAuth(`/documents/${documentId}/versions`);
}

export async function createDocumentVersion(documentId: string, data: {
    version_notes?: string;
    change_summary?: string;
}) {
    return fetchWithAuth(`/documents/${documentId}/versions`, {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function rollbackDocumentVersion(documentId: string, targetVersion: number, notes?: string) {
    return fetchWithAuth(`/documents/${documentId}/rollback`, {
        method: "POST",
        body: JSON.stringify({
            target_version_number: targetVersion,
            rollback_notes: notes,
        }),
    });
}

export async function getVersionDetails(documentId: string, versionNumber: number) {
    return fetchWithAuth(`/documents/${documentId}/versions/${versionNumber}`);
}

export async function exportConversationLogs(format: "jsonl" | "csv", params?: {
    user_id?: string;
    start_date?: string;
    end_date?: string;
}) {
    const queryParams = new URLSearchParams();
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                queryParams.append(key, value.toString());
            }
        });
    }
    const url = `/analytics/export/${format}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    
    const token = typeof window !== 'undefined' ? localStorage.getItem("supabase_token") : null;
    const headers: Record<string, string> = {};
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    const response = await fetch(`${getAPIUrl()}${url}`, {
        headers,
    });
    
    if (!response.ok) {
        throw new Error("Export failed");
    }
    
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `conversation_logs_${new Date().toISOString().split('T')[0]}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
}
