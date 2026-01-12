"use client";

import { useEffect, useRef, useCallback } from "react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import {
    SendIcon,
    Paperclip,
    LoaderIcon,
    Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";
import * as React from "react";

interface UseAutoResizeTextareaProps {
    minHeight: number;
    maxHeight?: number;
}

function useAutoResizeTextarea({
    minHeight,
    maxHeight,
}: UseAutoResizeTextareaProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const adjustHeight = useCallback(
        (reset?: boolean) => {
            const textarea = textareaRef.current;
            if (!textarea) return;

            if (reset) {
                textarea.style.height = `${minHeight}px`;
                return;
            }

            textarea.style.height = `${minHeight}px`;
            const newHeight = Math.max(
                minHeight,
                Math.min(
                    textarea.scrollHeight,
                    maxHeight ?? Number.POSITIVE_INFINITY
                )
            );

            textarea.style.height = `${newHeight}px`;
        },
        [minHeight, maxHeight]
    );

    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = `${minHeight}px`;
        }
    }, [minHeight]);

    return { textareaRef, adjustHeight };
}

interface AnimatedChatInputProps {
    value: string;
    onChange: (value: string) => void;
    onSend: () => void;
    onFileUpload?: (file: File) => void;
    isLoading?: boolean;
    placeholder?: string;
}

export function AnimatedChatInput({
    value,
    onChange,
    onSend,
    onFileUpload,
    isLoading = false,
    placeholder = "Ask a question or chat with the AI..."
}: AnimatedChatInputProps) {
    const [inputFocused, setInputFocused] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        minHeight: 60,
        maxHeight: 200,
    });

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (value.trim() && !isLoading) {
                onSend();
            }
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files?.[0];
        if (file && onFileUpload) {
            // Validate file type
            const allowedExtensions = ['.pdf', '.docx', '.txt', '.md'];
            const fileName = file.name.toLowerCase();
            const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));

            if (!isValid) {
                alert(`Invalid file type. Please upload only PDF, DOCX, TXT, or MD files.`);
                return;
            }
            onFileUpload(file);
        }
    };

    return (
        <motion.div
            className={cn(
                "relative backdrop-blur-2xl bg-white/[0.02] rounded-2xl border shadow-2xl transition-colors",
                isDragging ? "border-violet-500/50 bg-violet-500/10" : "border-white/[0.05]"
            )}
            initial={{ scale: 0.98 }}
            animate={{ scale: 1 }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            <div className="p-4">
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(e) => {
                        onChange(e.target.value);
                        adjustHeight();
                    }}
                    onKeyDown={handleKeyDown}
                    onFocus={() => setInputFocused(true)}
                    onBlur={() => setInputFocused(false)}
                    placeholder={isDragging ? "Drop file here..." : placeholder}
                    className="w-full px-4 py-3 resize-none bg-transparent border-none text-white/90 text-base md:text-lg focus:outline-none placeholder:text-white/20 min-h-[60px]"
                    style={{ overflow: "hidden" }}
                />
            </div>

            <div className="p-4 border-t border-white/[0.05] flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <input
                        type="file"
                        id="file-upload"
                        className="hidden"
                        accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
                        onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                                // Validate file type
                                const allowedExtensions = ['.pdf', '.docx', '.txt', '.md'];
                                const fileName = file.name.toLowerCase();
                                const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));

                                if (!isValid) {
                                    alert(`Invalid file type. Please upload only PDF, DOCX, TXT, or MD files.`);
                                    e.target.value = '';
                                    return;
                                }

                                if (onFileUpload) {
                                    onFileUpload(file);
                                }
                            }
                            // Reset input
                            e.target.value = '';
                        }}
                    />
                    <motion.label
                        htmlFor="file-upload"
                        whileTap={{ scale: 0.94 }}
                        className="p-2 text-white/40 hover:text-white/90 rounded-lg transition-colors cursor-pointer"
                    >
                        <Paperclip className="w-5 h-5" />
                    </motion.label>
                </div>

                <motion.button
                    type="button"
                    onClick={onSend}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.98 }}
                    disabled={isLoading || !value.trim()}
                    className={cn(
                        "px-6 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2",
                        value.trim()
                            ? "bg-white text-black shadow-lg"
                            : "bg-white/[0.05] text-white/40"
                    )}
                >
                    {isLoading ? (
                        <LoaderIcon className="w-4 h-4 animate-spin" />
                    ) : (
                        <SendIcon className="w-4 h-4" />
                    )}
                    <span className="text-base">Send</span>
                </motion.button>
            </div>
        </motion.div>
    );
}

export function TypingIndicator() {
    return (
        <motion.div
            className="flex items-center gap-3 px-4 py-3 backdrop-blur-2xl bg-white/[0.02] rounded-2xl border border-white/[0.05] max-w-fit"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
        >
            <div className="w-8 h-7 rounded-full bg-white/[0.05] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white/70" />
            </div>
            <div className="flex items-center gap-2 text-sm text-white/70">
                <span>Thinking</span>
                <div className="flex items-center ml-1">
                    {[1, 2, 3].map((dot) => (
                        <motion.div
                            key={dot}
                            className="w-1.5 h-1.5 bg-white/90 rounded-full mx-0.5"
                            animate={{
                                opacity: [0.3, 0.9, 0.3],
                                scale: [0.85, 1.1, 0.85]
                            }}
                            transition={{
                                duration: 1.2,
                                repeat: Infinity,
                                delay: dot * 0.15,
                            }}
                        />
                    ))}
                </div>
            </div>
        </motion.div>
    );
}
