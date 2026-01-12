"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { listDocuments, uploadFileWithAuth, deleteDocument, listFolderDocuments, reprocessDocument } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileText, Upload, MessageSquare, Loader2, CheckCircle2, Trash2, MoreVertical, XCircle, RefreshCw } from "lucide-react";
import { FolderTree } from "@/components/FolderTree";
import { motion } from "framer-motion";

export default function VaultPage() {
    const router = useRouter();
    const [documents, setDocuments] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
    const [selectedFolderName, setSelectedFolderName] = useState<string | null>(null);
    const [uploadFolderId, setUploadFolderId] = useState<string | null>(null);
    const [availableFolders, setAvailableFolders] = useState<any[]>([]);
    const [reprocessingId, setReprocessingId] = useState<string | null>(null);
    const [selectedFileName, setSelectedFileName] = useState<string>("");
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const checkSession = async () => {
            const { data } = await supabase.auth.getSession();
            if (!data.session) {
                router.push("/login");
            } else {
                // Refresh token in local storage securely if needed, but for now we rely on what was set in Login/Callback
                // Or we can just set it here again to be sure
                localStorage.setItem("supabase_token", data.session.access_token);
                loadDocuments(selectedFolderId);
            }
        };
        checkSession();
    }, [router]);

    const loadDocuments = async (folderId: string | null = null) => {
        try {
            setLoading(true);
            let docs;
            if (folderId) {
                docs = await listFolderDocuments(folderId);
            } else {
                docs = await listDocuments();
            }
            setDocuments(docs);
        } catch (e) {
            console.error("Failed to load docs", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDocuments(selectedFolderId);
    }, [selectedFolderId]);

    // Auto-refresh documents with "processing" status every 3 seconds
    useEffect(() => {
        const hasProcessingDocs = documents.some((doc) => doc.status === "processing");

        if (!hasProcessingDocs) {
            return; // No need to poll if no documents are processing
        }

        const interval = setInterval(() => {
            loadDocuments(selectedFolderId);
        }, 3000); // Poll every 3 seconds for faster updates

        return () => clearInterval(interval);
    }, [documents, selectedFolderId]);

    // Close menus when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.relative.inline-block')) {
                documents.forEach((doc) => {
                    const menu = document.getElementById(`menu-${doc.id}`);
                    if (menu) menu.classList.add("hidden");
                });
            }
        };

        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [documents]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            // Validate file type
            const allowedExtensions = ['.pdf', '.docx', '.txt', '.md'];
            const fileName = file.name.toLowerCase();
            const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));

            if (!isValid) {
                alert(`Invalid file type. Please upload only PDF, DOCX, TXT, or MD files.`);
                e.target.value = ''; // Clear the input
                setSelectedFileName("");
                return;
            }

            setSelectedFileName(file.name);
        } else {
            setSelectedFileName("");
        }
    };

    const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const file = formData.get("file") as File;
        const newFolderName = formData.get("new_folder_name") as string;
        if (!file) return;

        // Validate file type on submit
        const allowedExtensions = ['.pdf', '.docx', '.txt', '.md'];
        const fileName = file.name.toLowerCase();
        const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));

        if (!isValid) {
            alert(`Invalid file type. Please upload only PDF, DOCX, TXT, or MD files.`);
            return;
        }

        setUploading(true);
        try {
            // Upload with folder_id if selected, or create new folder if folder_name provided
            const uploadFormData = new FormData();
            uploadFormData.append("file", file);
            if (uploadFolderId) {
                uploadFormData.append("folder_id", uploadFolderId);
            }
            if (newFolderName && newFolderName.trim()) {
                uploadFormData.append("folder_name", newFolderName.trim());
            }

            const token = localStorage.getItem("supabase_token");
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/documents/upload`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                },
                body: uploadFormData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Upload failed" }));
                throw new Error(errorData.detail || "Upload failed");
            }

            setUploadDialogOpen(false);
            setUploadFolderId(null);
            setSelectedFileName("");
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
            loadDocuments(selectedFolderId);
        } catch (e: any) {
            alert(e.message || "Upload failed");
            console.error(e);
        } finally {
            setUploading(false);
        }
    };

    const handleLogout = async () => {
        await supabase.auth.signOut();
        localStorage.removeItem("supabase_token");
        router.push("/login");
    };

    const handleDelete = async (documentId: string, documentTitle: string) => {
        if (!confirm(`Are you sure you want to delete "${documentTitle}"? This action cannot be undone.`)) {
            return;
        }

        setDeletingId(documentId);
        try {
            await deleteDocument(documentId);
            // Reload documents after deletion
            loadDocuments();
        } catch (e) {
            alert("Failed to delete document");
            console.error(e);
        } finally {
            setDeletingId(null);
        }
    };

    const handleReprocess = async (documentId: string) => {
        setReprocessingId(documentId);
        try {
            await reprocessDocument(documentId);
            // Reload documents after a short delay to show the status change
            setTimeout(() => {
                loadDocuments(selectedFolderId);
            }, 1000);
        } catch (e: any) {
            console.error("Failed to reprocess document", e);
            alert(e.message || "Failed to reprocess document");
        } finally {
            setReprocessingId(null);
        }
    };

    const handleFolderSelect = (folderId: string | null) => {
        setSelectedFolderId(folderId);
        // Folder name will be set by FolderTree if needed
    };

    return (
        <div className="min-h-screen bg-[#0A0A0B] text-white flex">
            {/* Folder Sidebar */}
            <FolderTree
                selectedFolderId={selectedFolderId}
                onSelectFolder={handleFolderSelect}
                onFolderChange={() => loadDocuments(selectedFolderId)}
                onFolderListChange={setAvailableFolders}
                onLogout={handleLogout}
            />

            {/* Main Content */}
            <div className="flex-1 p-8 relative">
                {/* Background Gradients */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse" />
                    <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse delay-700" />
                </div>

                <div className="max-w-6xl mx-auto relative z-10">
                    <div className="flex justify-between items-center mb-8">
                        <div>
                            <div>
                                <h1 className="text-3xl font-bold tracking-tight text-white/90">
                                    Document Vault
                                </h1>
                                <p className="text-white/60 mt-2">
                                    {selectedFolderId ? `Folder: ${selectedFolderName || "Selected Folder"}` : "Upload and manage your documents"}
                                </p>
                            </div>
                        </div>
                        <div className="flex gap-2">

                            <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
                                <DialogTrigger asChild>
                                    <Button className="bg-violet-950 hover:bg-violet-900 text-white">
                                        <Upload className="mr-2 h-4 w-4" />
                                        Upload Document
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="bg-[#0A0A0B] border-white/10 text-white">
                                    <DialogHeader>
                                        <DialogTitle className="text-white">Upload Document</DialogTitle>
                                        <DialogDescription className="text-white/60">
                                            Upload PDF, DOCX, TXT, or MD files to the secure vault.
                                        </DialogDescription>
                                    </DialogHeader>
                                    <form onSubmit={handleUpload} className="space-y-4">
                                        <div className="grid w-full max-w-sm items-center gap-1.5">
                                            <Label htmlFor="file" className="text-white/70">Document</Label>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    ref={fileInputRef}
                                                    id="file"
                                                    name="file"
                                                    type="file"
                                                    accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
                                                    required
                                                    onChange={handleFileChange}
                                                    className="hidden"
                                                />
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    onClick={() => fileInputRef.current?.click()}
                                                    className="bg-white/5 border-white/10 text-white hover:bg-white/10 hover:text-white"
                                                >
                                                    Browse
                                                </Button>
                                                {selectedFileName && (
                                                    <span className="text-sm text-white/70 truncate max-w-[200px]">
                                                        {selectedFileName}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="grid w-full max-w-sm items-center gap-1.5">
                                            <Label htmlFor="folder" className="text-white/70">Folder (Optional)</Label>
                                            <select
                                                id="folder"
                                                value={uploadFolderId || ""}
                                                onChange={(e) => setUploadFolderId(e.target.value || null)}
                                                className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white ring-offset-background"
                                            >
                                                <option value="">No folder (root)</option>
                                                {availableFolders.map((folder) => (
                                                    <option key={folder.id} value={folder.id}>
                                                        {folder.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="grid w-full max-w-sm items-center gap-1.5">
                                            <Label htmlFor="new_folder_name" className="text-white/70">Or Create New Folder (Optional)</Label>
                                            <Input
                                                id="new_folder_name"
                                                name="new_folder_name"
                                                type="text"
                                                placeholder="Enter folder name"
                                                disabled={!!uploadFolderId}
                                                className="bg-white/5 border-white/10 text-white"
                                            />
                                            <p className="text-xs text-white/50">
                                                {uploadFolderId ? "Select 'No folder' above to create a new folder" : "Leave empty to use selected folder"}
                                            </p>
                                        </div>
                                        <Button
                                            type="submit"
                                            disabled={uploading}
                                            className="w-full bg-violet-950 hover:bg-violet-900 text-white"
                                        >
                                            {uploading ? "Uploading..." : "Upload"}
                                        </Button>
                                    </form>
                                </DialogContent>
                            </Dialog>
                        </div>
                    </div>

                    <Card className="bg-white/[0.02] border-white/[0.05] backdrop-blur-2xl">
                        <CardHeader>
                            <CardTitle className="text-white/90">Files</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {loading ? (
                                <p className="text-white/70">Loading documents...</p>
                            ) : documents.length === 0 ? (
                                <p className="text-white/50">No documents found. Upload one to get started.</p>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow className="border-white/10">
                                            <TableHead className="text-white/70">Name</TableHead>
                                            <TableHead className="text-white/70">Type</TableHead>
                                            <TableHead className="text-white/70">Status</TableHead>
                                            <TableHead className="text-white/70">Uploaded At</TableHead>
                                            <TableHead className="text-right text-white/70">Actions</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {documents.map((doc) => {
                                            const status = doc.status || "processing";
                                            const isDeleting = deletingId === doc.id;
                                            const isReprocessing = reprocessingId === doc.id;
                                            const isFailed = status === "failed";
                                            const isProcessing = status === "processing";
                                            const isCompleted = status === "completed";

                                            return (
                                                <TableRow key={doc.id} className="border-white/10 hover:bg-white/[0.02]">
                                                    <TableCell className="font-medium text-white/90">
                                                        <div className="flex items-center gap-2">
                                                            <FileText className="h-4 w-4 text-white/70" />
                                                            <span>{doc.title}</span>
                                                            {isFailed && (
                                                                <div className="relative inline-block">
                                                                    <button
                                                                        type="button"
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            // Close other menus
                                                                            documents.forEach((d) => {
                                                                                if (d.id !== doc.id) {
                                                                                    const otherMenu = document.getElementById(`menu-${d.id}`);
                                                                                    if (otherMenu) otherMenu.classList.add("hidden");
                                                                                }
                                                                            });
                                                                            // Toggle current menu
                                                                            const menu = document.getElementById(`menu-${doc.id}`);
                                                                            if (menu) {
                                                                                menu.classList.toggle("hidden");
                                                                            }
                                                                        }}
                                                                        className="p-1 hover:bg-white/10 rounded transition-colors"
                                                                        title="Reprocess options"
                                                                    >
                                                                        <MoreVertical className="h-4 w-4 text-white/50 hover:text-white/70" />
                                                                    </button>
                                                                    <div
                                                                        id={`menu-${doc.id}`}
                                                                        className="hidden absolute left-0 top-full mt-1 w-48 bg-[#0A0A0B] border border-white/10 rounded-md shadow-lg z-50"
                                                                        onClick={(e) => e.stopPropagation()}
                                                                    >
                                                                        <button
                                                                            type="button"
                                                                            onClick={async (e) => {
                                                                                e.stopPropagation();
                                                                                document.getElementById(`menu-${doc.id}`)?.classList.add("hidden");
                                                                                await handleReprocess(doc.id);
                                                                            }}
                                                                            disabled={isReprocessing}
                                                                            className="w-full text-left px-4 py-2 text-sm text-white/70 hover:bg-white/10 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                                                        >
                                                                            {isReprocessing ? (
                                                                                <>
                                                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                                                    Reprocessing...
                                                                                </>
                                                                            ) : (
                                                                                <>
                                                                                    <RefreshCw className="h-4 w-4" />
                                                                                    Reprocess
                                                                                </>
                                                                            )}
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="text-white/70">
                                                        <div className="relative inline-block max-w-[120px] overflow-hidden">
                                                            <span className="block truncate pr-4">{doc.mime_type?.split('/')[1]?.toUpperCase() || 'Unknown'}</span>
                                                            <div className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-l from-[#0A0A0B] via-[#0A0A0B]/80 to-transparent pointer-events-none"></div>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        {isCompleted ? (
                                                            <span className="flex items-center gap-1 text-green-400">
                                                                <CheckCircle2 className="h-3 w-3" />
                                                                <span className="text-xs">Completed</span>
                                                            </span>
                                                        ) : isFailed ? (
                                                            <span className="flex items-center gap-1 text-red-400">
                                                                <XCircle className="h-3 w-3" />
                                                                <span className="text-xs">Failed</span>
                                                            </span>
                                                        ) : isProcessing ? (
                                                            <span className="flex items-center gap-1 text-yellow-400">
                                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                                <span className="text-xs">Processing</span>
                                                            </span>
                                                        ) : (
                                                            <span className="flex items-center gap-1 text-white/50">
                                                                <span className="text-xs">Unknown</span>
                                                            </span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-white/70">{new Date(doc.created_at).toLocaleDateString()}</TableCell>
                                                    <TableCell className="text-right">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDelete(doc.id, doc.title)}
                                                            disabled={isDeleting}
                                                            className="text-red-400 hover:text-red-300 hover:bg-red-500/20"
                                                        >
                                                            {isDeleting ? (
                                                                <Loader2 className="h-4 w-4 animate-spin" />
                                                            ) : (
                                                                <Trash2 className="h-4 w-4" />
                                                            )}
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
