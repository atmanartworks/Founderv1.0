"use client";

export const dynamic = "force-dynamic";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import nextDynamic from "next/dynamic";
import { supabase } from "@/lib/supabase";
import { fetchWithAuth, getDocumentUrl, getAPIUrl, getFolderTree, createFolder } from "@/lib/api";
import { ChatSidebar } from "@/components/ChatSidebar";
import { AnimatedChatInput, TypingIndicator } from "@/components/AnimatedChatInput";
import { Card, CardContent } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Download, FileText, Folder, FolderPlus, Loader2, CheckCircle2, XCircle } from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

// Blinking cursor component
const BlinkingCursor = () => (
    <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ repeat: Infinity, duration: 0.8, ease: "easeInOut" }}
        className="inline-block w-2 h-4 bg-violet-400 ml-1 align-middle"
    />
);


// PDF Viewer removed - simplified citations don't need highlighting

interface Message {
    role: "user" | "assistant";
    content: string;
    citations?: any[];
    documents?: any[]; // For document list responses
    uploadedDocument?: any; // For uploaded documents in chat
    createdAt?: string;
}

export default function ChatPage() {
    const router = useRouter();
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const isActiveConversationRef = useRef(false);

    // File upload state
    const [uploadingFile, setUploadingFile] = useState(false);
    const [folderDialogOpen, setFolderDialogOpen] = useState(false);
    const [pendingFile, setPendingFile] = useState<File | null>(null);
    const [selectedUploadFolderId, setSelectedUploadFolderId] = useState<string | null>(null);
    const [availableFolders, setAvailableFolders] = useState<any[]>([]);
    const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0);

    useEffect(() => {
        const checkSession = async () => {
            const { data } = await supabase.auth.getSession();
            if (!data.session || !data.session.access_token) {
                router.push("/login");
            } else {
                localStorage.setItem("supabase_token", data.session.access_token);

                // Load persisted conversation ID
                const savedId = localStorage.getItem("lastActiveConversationId");
                if (savedId) {
                    setCurrentConversationId(savedId);
                }
            }
        };
        checkSession();
    }, [router]);

    // Persist current conversation ID
    useEffect(() => {
        if (currentConversationId) {
            localStorage.setItem("lastActiveConversationId", currentConversationId);
        }
    }, [currentConversationId]);

    // Load conversation when conversationId changes (e.g., from sidebar selection)
    // But don't reload if we're actively in a conversation (loading or streaming)
    useEffect(() => {
        if (currentConversationId) {
            // Only load if we're not actively in a conversation
            // This prevents flickering when creating a new conversation during message send
            if (!loading && !isActiveConversationRef.current && messages.length === 0) {
                loadConversation(currentConversationId);
            }
        } else {
            // If no conversation selected, start fresh
            setMessages([]);
            isActiveConversationRef.current = false;
        }
    }, [currentConversationId, loading]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Poll for document status updates
    useEffect(() => {
        const pollInterval = setInterval(async () => {
            const currentMessages = messagesRef.current;
            const processingDocs = currentMessages
                .filter(m => m.uploadedDocument && m.uploadedDocument.status === 'processing')
                .map(m => m.uploadedDocument.id);

            if (processingDocs.length === 0) return;

            try {
                const { data, error } = await supabase
                    .from('documents')
                    .select('id, status')
                    .in('id', processingDocs);

                if (error) throw error;

                if (data && data.length > 0) {
                    // Check if any status changed
                    let hasChanges = false;
                    data.forEach((doc: { id: string; status: string }) => {
                        const msg = currentMessages.find(m => m.uploadedDocument?.id === doc.id);
                        if (msg && msg.uploadedDocument && msg.uploadedDocument.status !== doc.status) {
                            hasChanges = true;
                        }
                    });

                    if (hasChanges) {
                        setMessages(prev => prev.map(msg => {
                            if (msg.uploadedDocument && processingDocs.includes(msg.uploadedDocument.id)) {
                                const updatedDoc = data.find((d: { id: string; status: string }) => d.id === msg.uploadedDocument!.id);
                                if (updatedDoc && updatedDoc.status !== 'processing') {
                                    return {
                                        ...msg,
                                        uploadedDocument: {
                                            ...msg.uploadedDocument,
                                            status: updatedDoc.status as any
                                        }
                                    };
                                }
                            }
                            return msg;
                        }));
                    }
                }
            } catch (e) {
                console.error("Error polling document status:", e);
            }
        }, 2000);

        return () => clearInterval(pollInterval);
    }, []);

    // Keep ref updated for polling
    const messagesRef = useRef(messages);
    useEffect(() => {
        messagesRef.current = messages;
    }, [messages]);


    const createNewConversation = async () => {
        try {
            const conv = await fetchWithAuth("/chat/conversations", {
                method: "POST",
                body: JSON.stringify({ title: "New Chat" })
            });
            setCurrentConversationId(conv.id);
            setMessages([]);
        } catch (e) {
            console.error("Failed to create conversation", e);
        }
    };

    const loadConversation = async (convId: string, preserveMessages: boolean = false) => {
        try {
            const msgs = await fetchWithAuth(`/chat/conversations/${convId}/messages`);
            // Transform messages from backend format to frontend format
            const transformedMessages: Message[] = msgs.map((msg: any) => ({
                role: msg.role,
                content: msg.content,
                citations: msg.citations ? (typeof msg.citations === 'string' ? JSON.parse(msg.citations) : msg.citations) : [],
                uploadedDocument: msg.uploaded_document ? {
                    id: msg.uploaded_document.id,
                    title: msg.uploaded_document.title,
                    status: msg.uploaded_document.status
                } : undefined,
                createdAt: msg.created_at
            }));

            // Only set messages if we're not preserving existing messages (e.g., during streaming)
            if (!preserveMessages || transformedMessages.length > 0) {
                setMessages(transformedMessages);
            }
            setCurrentConversationId(convId);
        } catch (e) {
            console.error("Failed to load messages", e);
            if (!preserveMessages) {
                setMessages([]);
            }
        }
    };

    // Load folders for folder selection dialog
    useEffect(() => {
        if (folderDialogOpen) {
            loadFolders();
        }
    }, [folderDialogOpen]);

    const loadFolders = async () => {
        try {
            const tree = await getFolderTree();
            // Flatten tree for selection
            const flattenFolders = (folders: any[]): any[] => {
                let result: any[] = [];
                folders.forEach(folder => {
                    result.push(folder);
                    if (folder.children && folder.children.length > 0) {
                        result = result.concat(flattenFolders(folder.children));
                    }
                });
                return result;
            };
            setAvailableFolders(flattenFolders(tree));
        } catch (e) {
            console.error("Failed to load folders", e);
        }
    };

    const handleFileUpload = async (file: File) => {
        // Validate file type
        const allowedExtensions = ['.pdf', '.docx', '.txt', '.md'];
        const fileName = file.name.toLowerCase();
        const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));

        if (!isValid) {
            alert(`Invalid file type. Please upload only PDF, DOCX, TXT, or MD files.`);
            return;
        }

        // Show folder selection dialog first
        setPendingFile(file);
        setFolderDialogOpen(true);
    };

    const handleFolderSelection = async () => {
        if (!pendingFile) return;

        setUploadingFile(true);
        setFolderDialogOpen(false);

        // Optimistic UI: Show "Uploading..." immediately
        const tempId = `temp-${Date.now()}`;
        setMessages((prev) => [...prev, {
            role: "user",
            content: `Uploading: ${pendingFile.name}`,
            uploadedDocument: {
                id: tempId,
                title: pendingFile.name,
                status: "uploading"
            },
            createdAt: new Date().toISOString()
        }]);

        let activeConversationId = currentConversationId;

        // Ensure we have a conversation ID
        if (!activeConversationId) {
            try {
                const conv = await fetchWithAuth("/chat/conversations", {
                    method: "POST",
                    body: JSON.stringify({ title: pendingFile.name.substring(0, 50) })
                });
                activeConversationId = conv.id;
                setCurrentConversationId(activeConversationId);
                setSidebarRefreshTrigger(prev => prev + 1);
            } catch (e) {
                console.error("Failed to create conversation for upload", e);
                setMessages(prev => prev.map(msg =>
                    msg.uploadedDocument?.id === tempId
                        ? { ...msg, uploadedDocument: { ...msg.uploadedDocument!, status: 'failed' } }
                        : msg
                ));
                setUploadingFile(false);
                return;
            }
        }

        if (!activeConversationId) {
            setMessages(prev => prev.map(msg =>
                msg.uploadedDocument?.id === tempId
                    ? { ...msg, uploadedDocument: { ...msg.uploadedDocument!, status: 'failed' } }
                    : msg
            ));
            setUploadingFile(false);
            return;
        }

        try {
            const formData = new FormData();
            formData.append("file", pendingFile);
            formData.append("conversation_id", activeConversationId);
            if (selectedUploadFolderId) {
                formData.append("folder_id", selectedUploadFolderId);
            }

            const token = localStorage.getItem("supabase_token");
            const response = await fetch(`${getAPIUrl()}/chat/upload-file`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` },
                body: formData
            });

            if (!response.ok) {
                throw new Error("Upload failed");
            }

            const result = await response.json();

            // Update optimistic message to "processing" with real ID
            setMessages(prev => prev.map(msg =>
                msg.uploadedDocument?.id === tempId
                    ? {
                        ...msg,
                        uploadedDocument: {
                            id: result.document_id,
                            title: result.title || pendingFile.name,
                            status: 'processing'
                        }
                    }
                    : msg
            ));

            // Add assistant confirmation
            setMessages((prev) => [...prev, {
                role: "assistant",
                content: `File "${pendingFile.name}" has been uploaded successfully. It's being processed and will be available shortly.`,
                citations: [],
                createdAt: new Date().toISOString()
            }]);

        } catch (e) {
            console.error("File upload error", e);
            // Update optimistic message to "failed"
            setMessages(prev => prev.map(msg =>
                msg.uploadedDocument?.id === tempId
                    ? { ...msg, uploadedDocument: { ...msg.uploadedDocument!, status: 'failed' } }
                    : msg
            ));
            setMessages((prev) => [...prev, {
                role: "assistant",
                content: "Sorry, I encountered an error uploading the file.",
                citations: []
            }]);
        } finally {
            setUploadingFile(false);
            setPendingFile(null);
            setSelectedUploadFolderId(null);
        }
    };

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        // Create conversation if none exists - MUST be done before sending message
        let activeConversationId = currentConversationId;
        let justCreatedConversation = false;

        // Mark as active conversation BEFORE any state changes to prevent useEffect from loading
        isActiveConversationRef.current = true;

        if (!activeConversationId) {
            try {
                // Create conversation with first message as title
                const conv = await fetchWithAuth("/chat/conversations", {
                    method: "POST",
                    body: JSON.stringify({ title: input.substring(0, 50) || "New Chat" })
                });
                activeConversationId = conv.id;
                justCreatedConversation = true;
                // Set conversation ID - useEffect won't load because isActiveConversationRef is true
                setCurrentConversationId(activeConversationId);
                // Refresh sidebar to show new conversation immediately
                setSidebarRefreshTrigger(prev => prev + 1);
            } catch (e) {
                console.error("Failed to create conversation", e);
                // If conversation creation fails, don't proceed
                isActiveConversationRef.current = false;
                setLoading(false);
                return;
            }
        }

        // Add user message to the conversation
        const userMessage: Message = { role: "user", content: input, createdAt: new Date().toISOString() };
        setMessages((prev) => {
            // If we just created a conversation, start fresh with user message
            // Otherwise, append to existing messages
            if (justCreatedConversation) {
                return [userMessage];
            }
            return [...prev, userMessage];
        });
        const query = input;
        setInput("");
        setLoading(true);

        // Check if streaming is enabled (default: true)
        const useStreaming = true;

        if (useStreaming) {
            // Streaming response
            try {
                const token = localStorage.getItem("supabase_token");
                const response = await fetch(`${getAPIUrl()}/chat/query`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        query: query,
                        conversation_id: activeConversationId,
                        stream: true
                    })
                });

                if (!response.ok) {
                    // Get error details from response
                    let errorMessage = `Streaming request failed (${response.status})`;
                    try {
                        const errorText = await response.text();
                        console.error("Streaming error response:", errorText);
                        try {
                            const errorData = JSON.parse(errorText);
                            errorMessage = errorData.detail || errorData.message || errorMessage;
                        } catch {
                            errorMessage = errorText || errorMessage;
                        }
                    } catch (e) {
                        console.error("Streaming request failed with status:", response.status, response.statusText);
                    }

                    // If 401, redirect to login
                    if (response.status === 401) {
                        window.location.href = '/login';
                        throw new Error("Session expired. Please log in again.");
                    }

                    throw new Error(errorMessage);
                }

                // Create assistant message placeholder
                const assistantMessage: Message = {
                    role: "assistant",
                    content: "",
                    citations: []
                };
                setMessages((prev) => [...prev, assistantMessage]);

                // Read stream
                const reader = response.body?.getReader();
                const decoder = new TextDecoder();

                if (!reader) {
                    throw new Error("No reader available");
                }

                let buffer = "";
                let citations: any[] = [];
                let assistantContent = "";
                let documents: any[] = [];

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n\n");
                    buffer = lines.pop() || "";

                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.content) {
                                    assistantContent += data.content;
                                    setMessages((prev) => {
                                        const newMessages = [...prev];
                                        const lastMsg = newMessages[newMessages.length - 1];
                                        if (lastMsg.role === "assistant") {
                                            lastMsg.content = assistantContent;
                                        }
                                        return newMessages;
                                    });
                                } else if (data.citation) {
                                    citations.push(data.citation);
                                    setMessages((prev) => {
                                        const newMessages = [...prev];
                                        const lastMsg = newMessages[newMessages.length - 1];
                                        if (lastMsg.role === "assistant") {
                                            lastMsg.citations = [...citations];
                                        }
                                        return newMessages;
                                    });
                                } else if (data.documents) {
                                    documents = data.documents;
                                    setMessages((prev) => {
                                        const newMessages = [...prev];
                                        const lastMsg = newMessages[newMessages.length - 1];
                                        if (lastMsg.role === "assistant") {
                                            lastMsg.documents = documents;
                                        }
                                        return newMessages;
                                    });
                                }
                            } catch (e) {
                                console.error("Error parsing chunk", e);
                            }
                        }
                    }
                }
            } catch (e) {
                console.error("Chat error", e);
                setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error." }]);
            } finally {
                setLoading(false);
                isActiveConversationRef.current = false;
            }
        }
    };

    // Simple markdown renderer - converts **text** to bold
    const renderMarkdown = (text: string) => {
        // Split by ** markers and render bold text
        const parts = text.split(/(\*\*.*?\*\*)/g);
        return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                const boldText = part.slice(2, -2);
                return <strong key={i} className="font-semibold">{boldText}</strong>;
            }
            return <span key={i}>{part}</span>;
        });
    };

    const handleCitationClick = async (citation: any) => {
        if (citation.document_id) {
            window.open(`/documents/${citation.document_id}`, '_blank');
        } else {
            // Fallback if no ID
            alert(`Document: ${citation.document_name || 'Unknown'}\n\n${citation.content || ''}`);
        }
    };

    const handleDocumentView = (documentId: string) => {
        // Open document in new page
        window.open(`/documents/${documentId}`, '_blank');
    };

    const renderMessage = (message: Message, index: number) => {
        if (message.role === "user") {
            return (
                <motion.div
                    key={index}
                    className="flex justify-end"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div className="max-w-2xl space-y-2">
                        {message.content && (
                            <div className="flex flex-col items-end gap-1">
                                <div className="px-5 py-4 bg-white/[0.05] rounded-2xl border border-white/[0.05]">
                                    <p className="text-white/90 text-base md:text-lg leading-relaxed">{message.content}</p>
                                </div>
                                {message.createdAt && (
                                    <span className="text-xs text-zinc-500 px-1">
                                        {new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                )}
                            </div>
                        )}
                        {message.uploadedDocument && (
                            <div className="px-5 py-4 bg-violet-500/10 rounded-2xl border border-violet-500/20 flex items-center gap-3">
                                {message.uploadedDocument.status === "completed" ? (
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ type: "spring", stiffness: 200, damping: 10 }}
                                    >
                                        <CheckCircle2 className="w-5 h-5 text-green-400" />
                                    </motion.div>
                                ) : message.uploadedDocument.status === "uploading" ? (
                                    <div className="relative">
                                        <div className="absolute inset-0 bg-violet-400 rounded-full opacity-20 animate-ping"></div>
                                        <Download className="w-5 h-5 text-violet-400 animate-bounce" />
                                    </div>
                                ) : message.uploadedDocument.status === "processing" ? (
                                    <Loader2 className="w-5 h-5 animate-spin text-violet-400" />
                                ) : message.uploadedDocument.status === "failed" ? (
                                    <XCircle className="w-5 h-5 text-red-400" />
                                ) : (
                                    <FileText className="w-5 h-5 text-violet-400" />
                                )}
                                <span className="text-white/90 text-base">{message.uploadedDocument.title}</span>
                                {message.uploadedDocument.id && !message.uploadedDocument.id.startsWith("temp-") && (
                                    <button
                                        onClick={() => handleDocumentView(message.uploadedDocument.id!)}
                                        className="ml-auto px-2 py-1 text-xs bg-violet-500/20 hover:bg-violet-500/30 text-violet-300 rounded transition-colors"
                                    >
                                        View
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                </motion.div>
            );
        }

        const isLastMessage = index === messages.length - 1;
        const isStreaming = loading && isLastMessage;
        const parts = message.content.split(/(\[\d+\])/g);

        return (
            <motion.div
                key={index}
                className="flex justify-start"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <div className="max-w-2xl space-y-3">
                    <div className="px-5 py-4 bg-white/[0.02] rounded-2xl border border-white/[0.05]">
                        <div className="text-white/90 text-base md:text-lg whitespace-pre-wrap leading-relaxed">
                            {parts.map((part, i) => {
                                if (/\[\d+\]/.test(part)) {
                                    const citationNum = parseInt(part.replace(/[\[\]]/g, ""));
                                    const citation = message.citations?.[citationNum - 1];
                                    if (citation) {
                                        return (
                                            <span
                                                key={i}
                                                onClick={() => handleCitationClick(citation)}
                                                className="relative group inline-flex items-center justify-center w-6 h-6 text-[10px] font-medium text-violet-300 bg-violet-500/20 rounded-full ml-1 mr-1 cursor-pointer hover:bg-violet-500/30 transition-colors"
                                                title={`${citation.document_name || 'Document'}${citation.page_number ? ` - Page ${citation.page_number}` : ''}`}
                                            >
                                                {part.replace(/[\[\]]/g, "")}
                                                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 w-72 bg-gray-900 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 border border-white/10">
                                                    <div className="font-semibold mb-1 text-violet-300">{citation.document_name || 'Document'}</div>
                                                    {citation.page_number && (
                                                        <div className="text-violet-400 mb-2 text-[11px]">Page {citation.page_number}</div>
                                                    )}
                                                    {citation.content && (
                                                        <div className="text-white/70 text-[11px] line-clamp-5 whitespace-pre-wrap">{citation.content}</div>
                                                    )}
                                                    <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                                                </div>
                                            </span>
                                        );
                                    }
                                }
                                return <span key={i}>{renderMarkdown(part)}</span>;
                            })}
                            {/* Blinking cursor aligned with text */}
                            {isStreaming && <BlinkingCursor />}
                        </div>
                    </div>

                    {message.citations && message.citations.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-white/10">
                            <p className="text-xs text-white/50 font-medium mb-2">Resources:</p>
                            <div className="flex flex-wrap gap-2">
                                {message.citations.map((citation: any, idx: number) => (
                                    <button
                                        key={idx}
                                        onClick={() => handleCitationClick(citation)}
                                        className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/20 rounded-full transition-colors max-w-xs truncate"
                                        title={`${citation.document_name || 'Document'}${citation.page_number ? ` - Page ${citation.page_number}` : ''}`}
                                    >
                                        <FileText className="w-3 h-3 flex-shrink-0" />
                                        <span className="truncate">{citation.document_name || `Source ${idx + 1}`}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </motion.div>
        );
    };

    return (
        <div className="flex h-screen bg-[#0A0A0B] text-white overflow-hidden">
            {/* Sidebar */}
            <ChatSidebar
                currentConversationId={currentConversationId}
                onSelectConversation={(id) => {
                    loadConversation(id);
                }}
                onNewChat={() => {
                    setCurrentConversationId(null);
                    localStorage.removeItem("lastActiveConversationId");
                    setMessages([]);
                }}
                refreshTrigger={sidebarRefreshTrigger}
            />

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col relative">
                {/* Background Gradients */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse" />
                    <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse delay-700" />
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 relative z-10">
                    {messages.length === 0 ? (
                        <div className="flex items-center justify-center h-full">
                            <motion.div
                                className="text-center space-y-3 max-w-2xl"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                            >
                                <div className="flex items-center justify-center mb-4">
                                    <Image
                                        src="/logo-full.svg"
                                        alt="FounderGPT Logo"
                                        width={120}
                                        height={120}
                                        className="w-32 h-32"
                                    />
                                </div>
                                <h1 className="text-2xl font-medium bg-clip-text text-transparent bg-gradient-to-r from-white/90 to-white/40">
                                    How can I help today?
                                </h1>
                                <p className="text-sm text-white/40">
                                    Ask questions about your uploaded documents
                                </p>
                            </motion.div>
                        </div>
                    ) : (
                        <>
                            {messages.map((message, index) => renderMessage(message, index))}
                            {loading && messages.length > 0 && messages[messages.length - 1].role === 'user' && <TypingIndicator />}
                            <div ref={messagesEndRef} />
                        </>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-6 relative z-10">
                    <div className="max-w-3xl mx-auto">
                        <AnimatedChatInput
                            value={input}
                            onChange={setInput}
                            onSend={handleSend}
                            onFileUpload={handleFileUpload}
                            isLoading={loading || uploadingFile}
                        />
                    </div>
                </div>
            </div>

            {/* Folder Selection Dialog */}
            <Dialog open={folderDialogOpen} onOpenChange={setFolderDialogOpen}>
                <DialogContent className="bg-[#0A0A0B] border-white/10 text-white">
                    <DialogHeader>
                        <DialogTitle>Select Folder</DialogTitle>
                        <DialogDescription className="text-white/60">
                            Choose a folder to upload the document to, or leave empty for root.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div>
                            <Label className="text-white/70 mb-2 block">Folder</Label>
                            <select
                                value={selectedUploadFolderId || ""}
                                onChange={(e) => setSelectedUploadFolderId(e.target.value || null)}
                                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                            >
                                <option value="">Root (No folder)</option>
                                {availableFolders.map((folder) => (
                                    <option key={folder.id} value={folder.id}>
                                        {folder.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        {pendingFile && (
                            <div className="px-3 py-2 bg-white/5 rounded-lg border border-white/10">
                                <div className="flex items-center gap-2">
                                    <FileText className="h-4 w-4 text-violet-400" />
                                    <span className="text-sm text-white/90">{pendingFile.name}</span>
                                    <span className="text-xs text-white/50 ml-auto">
                                        {(pendingFile.size / 1024 / 1024).toFixed(2)} MB
                                    </span>
                                </div>
                            </div>
                        )}
                        <div className="flex justify-end gap-2">
                            <Button
                                variant="outline"
                                onClick={() => {
                                    setFolderDialogOpen(false);
                                    setPendingFile(null);
                                    setSelectedUploadFolderId(null);
                                }}
                                className="bg-white/5 border-white/10 text-white hover:bg-white/10"
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleFolderSelection}
                                disabled={uploadingFile}
                                className="bg-violet-500 hover:bg-violet-600 text-white"
                            >
                                {uploadingFile ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                        Uploading...
                                    </>
                                ) : (
                                    "Upload"
                                )}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
