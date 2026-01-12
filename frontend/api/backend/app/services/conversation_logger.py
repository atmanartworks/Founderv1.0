"""
Conversation Logger Service
Stores conversation data for analytics, auditing, and training data export.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime

from app.db.supabase import get_supabase_client
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConversationLogger:
    """Service for logging conversations to analytics database."""
    
    def __init__(self):
        self.db = get_supabase_client()
    
    def log_conversation(
        self,
        user: User,
        conversation_id: UUID,
        user_prompt: str,
        assistant_response: str,
        retrieved_chunks: List[Dict[str, Any]],
        citations: List[Dict[str, Any]],
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tokens_used: int = None,
        session_metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Log a conversation interaction for analytics and training.
        
        Args:
            user: The user who made the request
            conversation_id: The conversation ID
            user_prompt: The user's query/prompt
            assistant_response: The assistant's response
            retrieved_chunks: List of chunks retrieved for RAG
            citations: List of citation objects from response
            model_name: Model used (default: from settings)
            temperature: Temperature used (default: from settings)
            max_tokens: Max tokens used (default: from settings)
            tokens_used: Actual tokens consumed
            session_metadata: Additional session context
        
        Returns:
            Log ID if successful, None otherwise
        """
        try:
            # Extract document IDs from chunks
            document_ids = set()
            for chunk in retrieved_chunks:
                if "document_id" in chunk:
                    document_ids.add(chunk["document_id"])
            
            # Get document info
            documents = []
            if document_ids:
                doc_response = self.db.table("documents").select("id, title, folder_id").in_("id", list(document_ids)).execute()
                documents = doc_response.data if doc_response.data else []
            
            # Prepare retrieved chunks data (simplified for storage)
            chunks_data = []
            for chunk in retrieved_chunks:
                chunks_data.append({
                    "chunk_id": chunk.get("id"),
                    "document_id": chunk.get("document_id"),
                    "content_preview": chunk.get("content", "")[:200],  # First 200 chars
                    "similarity": chunk.get("similarity"),
                    "page_number": chunk.get("page_number"),
                    "chunk_index": chunk.get("chunk_index")
                })
            
            # Prepare documents data
            docs_data = []
            for doc in documents:
                docs_data.append({
                    "document_id": doc.get("id"),
                    "title": doc.get("title"),
                    "folder_id": doc.get("folder_id")
                })
            
            # Build log entry
            log_entry = {
                "user_id": str(user.id),
                "conversation_id": str(conversation_id),
                "user_role": user.role.value,
                "user_prompt": user_prompt,
                "assistant_response": assistant_response,
                "retrieved_chunks": chunks_data,
                "retrieved_documents": docs_data,
                "citations": citations,
                "model_name": model_name or settings.OPENAI_MODEL,
                "temperature": temperature or 0.7,
                "max_tokens": max_tokens or 2000,
                "tokens_used": tokens_used,
                "session_metadata": session_metadata or {}
            }
            
            # Insert log
            result = self.db.table("conversation_logs").insert(log_entry).execute()
            
            if result.data:
                log_id = result.data[0].get("id")
                logger.info(f"Logged conversation {log_id} for user {user.id}")
                return log_id
            else:
                logger.warning(f"Failed to log conversation: no data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error logging conversation: {str(e)}", exc_info=True)
            return None
    
    def get_conversation_logs(
        self,
        user_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation logs with filters.
        
        Args:
            user_id: Filter by user ID
            conversation_id: Filter by conversation ID
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of conversation log entries
        """
        try:
            query = self.db.table("conversation_logs").select("*")
            
            if user_id:
                query = query.eq("user_id", str(user_id))
            if conversation_id:
                query = query.eq("conversation_id", str(conversation_id))
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            query = query.order("created_at", desc=True).limit(limit).offset(offset)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error retrieving conversation logs: {str(e)}", exc_info=True)
            return []
    
    def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get analytics summary for conversation logs.
        
        Returns:
            Dictionary with analytics metrics
        """
        try:
            query = self.db.table("conversation_logs").select("*")
            
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            result = query.execute()
            logs = result.data if result.data else []
            
            # Calculate metrics
            total_logs = len(logs)
            unique_users = len(set(log["user_id"] for log in logs))
            unique_conversations = len(set(log["conversation_id"] for log in logs))
            
            # Average response length
            response_lengths = [len(log.get("assistant_response", "")) for log in logs]
            avg_response_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0
            
            # Average prompt length
            prompt_lengths = [len(log.get("user_prompt", "")) for log in logs]
            avg_prompt_length = sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0
            
            # Documents referenced
            all_doc_ids = set()
            for log in logs:
                for doc in log.get("retrieved_documents", []):
                    if "document_id" in doc:
                        all_doc_ids.add(doc["document_id"])
            
            # Citations per response
            citations_counts = [len(log.get("citations", [])) for log in logs]
            avg_citations = sum(citations_counts) / len(citations_counts) if citations_counts else 0
            
            # By role
            logs_by_role = {}
            for log in logs:
                role = log.get("user_role", "unknown")
                logs_by_role[role] = logs_by_role.get(role, 0) + 1
            
            return {
                "total_logs": total_logs,
                "unique_users": unique_users,
                "unique_conversations": unique_conversations,
                "avg_response_length": round(avg_response_length, 2),
                "avg_prompt_length": round(avg_prompt_length, 2),
                "unique_documents_referenced": len(all_doc_ids),
                "avg_citations_per_response": round(avg_citations, 2),
                "logs_by_role": logs_by_role,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating analytics: {str(e)}", exc_info=True)
            return {}
    
    def export_to_jsonl(
        self,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Export conversation logs to JSONL format for training.
        
        Returns:
            JSONL string
        """
        logs = self.get_conversation_logs(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        jsonl_lines = []
        for log in logs:
            # Format for training data
            training_entry = {
                "messages": [
                    {
                        "role": "user",
                        "content": log.get("user_prompt", "")
                    },
                    {
                        "role": "assistant",
                        "content": log.get("assistant_response", "")
                    }
                ],
                "metadata": {
                    "conversation_id": log.get("conversation_id"),
                    "user_role": log.get("user_role"),
                    "retrieved_documents": log.get("retrieved_documents", []),
                    "citations": log.get("citations", []),
                    "model_name": log.get("model_name"),
                    "created_at": log.get("created_at")
                }
            }
            jsonl_lines.append(json.dumps(training_entry))
        
        return "\n".join(jsonl_lines)
    
    def export_to_csv(
        self,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Export conversation logs to CSV format.
        
        Returns:
            CSV string
        """
        import csv
        import io
        
        logs = self.get_conversation_logs(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "id", "user_id", "conversation_id", "user_role", "user_prompt",
            "assistant_response", "num_citations", "num_documents", "model_name",
            "created_at"
        ])
        
        # Rows
        for log in logs:
            writer.writerow([
                log.get("id"),
                log.get("user_id"),
                log.get("conversation_id"),
                log.get("user_role"),
                log.get("user_prompt", "")[:500],  # Truncate for CSV
                log.get("assistant_response", "")[:500],
                len(log.get("citations", [])),
                len(log.get("retrieved_documents", [])),
                log.get("model_name"),
                log.get("created_at")
            ])
        
        return output.getvalue()


# Singleton instance
conversation_logger = ConversationLogger()

