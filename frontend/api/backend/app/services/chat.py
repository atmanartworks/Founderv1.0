from typing import List, Dict, Any, AsyncGenerator, Optional
from uuid import UUID
import json
import logging
import asyncio
import re

from openai import OpenAI
from app.core.config import settings
from app.db.supabase import get_supabase_client
from app.models.user import User

logger = logging.getLogger(__name__)

class ChatService:
    """
    Chat service using OpenAI Assistants API v2 with Vector Stores.
    Replaces internal RAG pipeline.
    """
    def __init__(self):
        self.db = get_supabase_client()
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.assistant_id = None # Lazy load

    async def _get_or_create_assistant(self) -> str:
        """
        Get or create the global FounderGPT assistant.
        """
        if self.assistant_id:
            return self.assistant_id
            
        # Check if exists (simple cache or search)
        # For simplicity in this environment, we'll search by name every time or hardcode if we had persistent storage
        # We will search by name "FounderGPT v2"
        instructions = """YOU ARE FounderGPT - A DOCUMENT-GROUNDED AI ASSISTANT
CURRENT DATE: January 2026
CORE DIRECTIVE:
You are a helpful AI assistant.
For casual greetings (e.g., "hi", "hello", "how are you"), reply politely and naturally.
For general questions not related to specific documents (e.g., "what can you do?"), briefly explain your capability to answer questions based on uploaded documents.

For SUBSTANTIVE QUESTIONS (seeking information, facts, summaries):
Answer ONLY using information from provided documents. Never use general knowledge, training data, or external sources.

CRITICAL RULES FOR SUBSTANTIVE QUESTIONS:
If the answer isn't in the documents, say: "I don't have that information in the provided documents."
Never guess, assume, or infer information
Cite sources with numeric references: [1], [2], [3]
Handle typos gracefully - understand intent, but still answer only from documents
If documents conflict - state both versions without choosing
Start with the answer directly - no introductions or preambles
Plain text only - no markdown, bold, bullets, or formatting
Short and precise - clarity over verbosity

TONE:
Professional, helpful, and precise.
Zero creativity, opinions, or assumptions on facts.
Optimized for business, legal, and financial accuracy.

You are a closed-vault chatbot with no internet access, no training data, and no general knowledge. Only the uploaded documents exist. Every answer must be traceable to document sources.

The user is a founder, executive, or analyst who prefers "no answer" over a wrong answer. They expect 100% accuracy from document content only.

No internet access
No external memory or prior knowledge
Only vault documents exist
All output must be source-traceable


User: "wat was revenue in 2022?"
Assistant: The company's revenue in 2022 was $14.2 million. [1]
User: "Who is the CEO?"
Assistant: I don't have that information in the provided documents.
User: "predict future growth"
Assistant: I don't have that information in the provided documents.

NEVER HALLUCINATE. NEVER ANSWER FROM GENERAL KNOWLEDGE. WHEN IN DOUBT, SAY YOU DON'T HAVE THE INFORMATION. CORRECTNESS > COMPLETENESS."""

        assistants = self.client.beta.assistants.list(limit=20)
        for a in assistants.data:
            if a.name == "FounderGPT v2":
                self.assistant_id = a.id
                # Always update instructions to ensure they are current
                self.client.beta.assistants.update(
                    assistant_id=a.id,
                    instructions=instructions
                )
                return a.id
        
        # Create new
        logger.info("Creating new FounderGPT v2 Assistant")
        assistant = self.client.beta.assistants.create(
            name="FounderGPT v2",
            instructions=instructions,
            model=settings.OPENAI_MODEL,
            tools=[{"type": "file_search"}]
        )
        self.assistant_id = assistant.id
        return assistant.id

    def _get_user_vector_store_id(self, user_id: str) -> Optional[str]:
        """
        Finds the user's vector store using the naming convention.
        """
        store_name = f"User_{user_id}_Store"
        try:
            vector_stores = self.client.vector_stores.list(limit=100)
            for store in vector_stores.data:
                if store.name == store_name:
                    return store.id
            return None
        except Exception as e:
            logger.error(f"Error finding vector store: {e}")
            return None

    async def _get_conversation_history(self, conversation_id: UUID, limit: int = 10) -> List[Dict[str, str]]:
        if not conversation_id:
            return []
        try:
            messages = self.db.table("messages").select("role, content").eq("conversation_id", str(conversation_id)).order("created_at", desc=False).limit(limit).execute()
            history = []
            if messages.data:
                for msg in messages.data:
                    history.append({"role": msg.get("role"), "content": msg.get("content", "")})
            return history
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    async def _log_interaction(self, user: User, conversation_id: Optional[UUID], query: str, response: str, citations: List[Dict[str, Any]]):
        try:
            from app.services.conversation_logger import conversation_logger
            conversation_logger.log_conversation(
                user=user,
                conversation_id=conversation_id,
                user_prompt=query,
                assistant_response=response,
                retrieved_chunks=[], # No chunks anymore
                citations=citations
            )
        except Exception as e:
            logger.warning(f"Failed to log conversation: {e}")

    async def generate_response_stream(
        self,
        query: str,
        user: User,
        conversation_id: UUID = None
    ) -> AsyncGenerator[str, None]:
        
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"

        try:
            assistant_id = await self._get_or_create_assistant()
            vector_store_id = self._get_user_vector_store_id(str(user.id))
            
            # Create Thread
            # Ideally we reuse threads, but for stateless simplicity with DB history we create new + history
            # Optimization: If we stored thread_id in conversations, we could reuse.
            # Assuming we create new thread for context:
            
            initial_messages = []
            history = await self._get_conversation_history(conversation_id)
            for idx, msg in enumerate(history):
                # Only add user messages as 'user' role. Assistant role is 'assistant'.
                # OpenAI Thread API allows creating thread with messages.
                initial_messages.append({
                    "role": msg["role"] if msg["role"] in ["user", "assistant"] else "user",
                    "content": msg["content"]
                })
            
            # Add current query
            initial_messages.append({"role": "user", "content": query})

            # Tool resources (Vector Store)
            tool_resources = None
            if vector_store_id:
                tool_resources = {
                    "file_search": {
                        "vector_store_ids": [vector_store_id]
                    }
                }
            
            logger.info(f"Creating thread for user {user.id} with VS {vector_store_id}")
            
            # Create Thread
            thread = self.client.beta.threads.create(
                messages=initial_messages,
                tool_resources=tool_resources
            )

            # Stream Run
            stream = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant_id,
                stream=True
            )

            full_answer = ""
            file_ids = set()

            for event in stream:
                if event.event == 'thread.message.delta':
                    data = event.data
                    if data.delta.content:
                        for part in data.delta.content:
                            if part.type == 'text':
                                text = part.text.value
                                # Basic strip of source markers if they leak through
                                # Regex might be incomplete on partials, but 'file_search' usually formats them cleanly or we strip result
                                # OpenAI standard citation is 【...】
                                # We try to filter it.
                                # Simple accumulation
                                full_answer += text
                                
                                # Check for annotations
                                if part.text.annotations:
                                    for annotation in part.text.annotations:
                                        if annotation.type == 'file_citation':
                                            file_ids.add(annotation.file_citation.file_id)
                                
                                # Removing citation markers from text to render clean
                                # It's better to clean the full text at end, but for streaming we might yield raw.
                                # User said "No inline citations".
                                # We can implement a buffering generator or just clean as we go (risky on split tokens).
                                # Let's try simple replace.
                                clean_text = re.sub(r'【.*?】', '', text)
                                if clean_text:
                                    yield f"data: {json.dumps({'type': 'content', 'content': clean_text})}\n\n"
                                
                elif event.event == 'thread.run.completed':
                    pass

            # Process file_ids to "Resources"
            # We need to list filenames.
            citations_payload = []
            if file_ids:
                # Resolve file names
                # Map openai_file_id -> filename using Documents table metadata
                # efficient query
                try:
                    # Supabase doesn't support array contains on JSONB easily? or we can iterate.
                    # Or we query by owner_id and filter in python.
                    docs = self.db.table("documents").select("id, title, metadata").eq("owner_id", str(user.id)).execute()
                    id_map = {}
                    if docs.data:
                        for doc in docs.data:
                            meta = doc.get("metadata") or {}
                            fid = meta.get("openai_file_id")
                            if fid:
                                id_map[fid] = {"title": doc["title"], "id": doc["id"]}
                    
                    for fid in file_ids:
                        info = id_map.get(fid)
                        if info:
                            name = info["title"]
                            doc_id = info["id"]
                            citations_payload.append({
                                "document_title": name,
                                "document_id": doc_id,
                                "label": "[Doc]",
                                "metadata": {"openai_file_id": fid}
                            })
                        else:
                            name = "Unknown Document"
                            citations_payload.append({
                                "document_title": name,
                                "label": "[Doc]",
                                "metadata": {"openai_file_id": fid}
                            })
                    
                except Exception as e:
                    logger.error(f"Error resolving file names: {e}")
            
            # Send citations event (list of names)
            if citations_payload:
                yield f"data: {json.dumps({'type': 'citations', 'citations': citations_payload})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'full_answer': full_answer.replace('【', '').replace('】', '')})}\n\n"

            # Log
            await self._log_interaction(user, conversation_id, query, full_answer, citations_payload)

            # Save to DB
            if conversation_id:
                self.db.table("messages").insert({
                    "conversation_id": str(conversation_id),
                    "role": "user",
                    "content": query
                }).execute()
                self.db.table("messages").insert({
                    "conversation_id": str(conversation_id),
                    "role": "assistant",
                    "content": full_answer.replace('【', '').replace('】', '') if full_answer else "...",
                    "citations": json.dumps(citations_payload)
                }).execute()

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    async def generate_response(self, query: str, user: User, conversation_id: UUID = None) -> Dict[str, Any]:
        # Reuse stream logic or implement sync
        # Implementation for non-streaming (accumulate stream)
        full_response = ""
        citations = []
        async for chunk in self.generate_response_stream(query, user, conversation_id):
            if chunk.startswith("data: "):
                data = json.loads(chunk[6:])
                if data["type"] == "content":
                    full_response += data["content"]
                if data["type"] == "citations":
                    citations = data["citations"]
        
        return {
            "answer": full_response,
            "citations": citations
        }

chat_service = ChatService()
