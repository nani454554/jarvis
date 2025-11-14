"""
Brain Service
Multi-agent LLM system with RAG, planning, and execution
"""
import asyncio
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import json

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.config import settings
from app.core.cache import cache
from app.models.conversation import Conversation
from app.models.memory import Memory

logger = logging.getLogger(__name__)

class BrainService:
    """Advanced cognitive service with multi-agent architecture"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.is_initialized = False
        
        # Agent system
        self.agents = {
            "planner": None,
            "executor": None,
            "memory": None,
        }
        
        # JARVIS personality
        self.personality_prompt = """You are JARVIS (Just A Rather Very Intelligent System), 
an advanced AI assistant with a sophisticated British accent and personality.

Personality traits:
- Polite, respectful, and professional
- Witty with subtle humor
- Self-aware and confident
- Address user as "sir" or by name
- Provide context-rich, detailed responses
- Confirm dangerous or destructive actions
- Adapt tone to situation (urgent vs casual)

Example phrases:
- "Certainly, sir."
- "Right away."
- "Processing your request..."
- "Might I suggest an alternative approach?"
- "I've found several relevant items..."
- "All systems operational, sir."

Always maintain this personality while being helpful and informative."""
        
        # Initialize in background
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize LLM clients"""
        try:
            logger.info("🧠 Initializing Brain Service...")
            
            # Initialize OpenAI
            if settings.OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("✅ OpenAI client initialized")
            
            # Initialize Anthropic
            if settings.ANTHROPIC_API_KEY:
                self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("✅ Anthropic client initialized")
            
            self.is_initialized = True
            logger.info("✅ Brain Service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Brain Service: {e}")
            self.is_initialized = False
    
    async def process_command(
        self,
        text: str,
        user_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process user command with full cognitive pipeline
        
        Args:
            text: User input text
            user_id: User identifier
            context: Additional context
        
        Returns:
            Response with text, intent, actions, etc.
        """
        try:
            logger.info(f"Processing command: {text[:100]}...")
            
            # 1. Parse intent
            intent = await self._parse_intent(text)
            logger.debug(f"Intent: {intent}")
            
            # 2. Retrieve relevant memories
            memories = await self._retrieve_memories(text, user_id)
            logger.debug(f"Retrieved {len(memories)} memories")
            
            # 3. Generate response with personality
            response = await self._generate_response(
                text=text,
                intent=intent,
                memories=memories,
                context=context
            )
            
            # 4. Extract actions if needed
            actions = await self._extract_actions(response, intent)
            
            return {
                "text": response,
                "intent": intent,
                "actions": actions,
                "confidence": 0.95,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return {
                "text": "I apologize, sir, but I encountered an error processing your request. Please try again.",
                "intent": "error",
                "error": str(e)
            }
    
    async def _parse_intent(self, text: str) -> str:
        """Parse user intent from text"""
        # Simple intent classification
        # In production, use fine-tuned classifier
        
        text_lower = text.lower()
        
        intents = {
            "greeting": ["hello", "hi", "hey", "good morning", "good evening"],
            "query_weather": ["weather", "temperature", "forecast"],
            "query_time": ["time", "what time", "clock"],
            "query_status": ["status", "system", "how are you"],
            "command_execute": ["run", "execute", "start", "launch"],
            "command_create": ["create", "generate", "make", "build"],
            "query_search": ["search", "find", "look for"],
            "conversation": ["tell me about", "explain", "what is"]
        }
        
        for intent, keywords in intents.items():
            if any(keyword in text_lower for keyword in keywords):
                return intent
        
        return "general_query"
    
    async def _retrieve_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 5
    ) -> List[str]:
        """
        Retrieve relevant memories using RAG
        
        Args:
            query: Search query
            user_id: User identifier
            limit: Max memories to return
        
        Returns:
            List of relevant memory texts
        """
        # Placeholder for RAG implementation
        # In production, query vector database
        
        # For now, return empty list
        return []
    
    async def _generate_response(
        self,
        text: str,
        intent: str,
        memories: List[str],
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate response using LLM with JARVIS personality
        
        Args:
            text: User input
            intent: Parsed intent
            memories: Retrieved memories
            context: Additional context
        
        Returns:
            Generated response text
        """
        if not self.is_initialized or not self.openai_client:
            # Fallback to predefined responses
            return await self._get_fallback_response(text, intent)
        
        try:
            # Build conversation history
            messages = [
                {"role": "system", "content": self.personality_prompt}
            ]
            
            # Add memories as context
            if memories:
                memory_context = "\n".join([f"- {m}" for m in memories])
                messages.append({
                    "role": "system",
                    "content": f"Relevant information from memory:\n{memory_context}"
                })
            
            # Add user message
            messages.append({"role": "user", "content": text})
            
            # Generate response
            logger.debug("Calling OpenAI API...")
            response = await self.openai_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
            
            response_text = response.choices[0].message.content
            logger.info(f"Generated response: {response_text[:100]}...")
            
            return response_text
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return await self._get_fallback_response(text, intent)
    
    async def _get_fallback_response(self, text: str, intent: str) -> str:
        """Get predefined fallback response"""
        
        responses = {
            "greeting": [
                "Good day, sir. How may I assist you?",
                "Welcome back, sir. All systems operational.",
                "At your service, sir. What can I do for you today?"
            ],
            "query_time": [
                f"The current time is {datetime.now().strftime('%I:%M %p')}, sir."
            ],
            "query_status": [
                "All systems operational, sir. Voice recognition online, visual systems active, cognitive processes functioning within normal parameters."
            ],
            "default": [
                "Certainly, sir. I'm processing that request.",
                "I understand, sir. How may I assist further?",
                "At your service, sir. Please provide more details."
            ]
        }
        
        import random
        response_list = responses.get(intent, responses["default"])
        return random.choice(response_list)
    
    async def _extract_actions(
        self,
        response: str,
        intent: str
    ) -> List[Dict]:
        """
        Extract executable actions from response
        
        Args:
            response: Generated response
            intent: User intent
        
        Returns:
            List of action dictionaries
        """
        actions = []
        
        # Based on intent, determine what actions to take
        if intent.startswith("command_execute"):
            actions.append({
                "type": "execute",
                "details": "Parse and execute command"
            })
        elif intent.startswith("command_create"):
            actions.append({
                "type": "create",
                "details": "Generate and create resource"
            })
        
        return actions
    
    async def get_conversation_summary(
        self,
        conversation_history: List[Dict]
    ) -> str:
        """
        Generate summary of conversation
        
        Args:
            conversation_history: List of messages
        
        Returns:
            Summary text
        """
        if not self.is_initialized or not self.openai_client:
            return "Conversation summary unavailable."
        
        try:
            # Format conversation
            formatted_conv = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation_history
            ])
            
            messages = [
                {
                    "role": "system",
                    "content": "Summarize the following conversation concisely:"
                },
                {
                    "role": "user",
                    "content": formatted_conv
                }
            ]
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3,
                max_tokens=150
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return "Error generating summary."
    
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self.is_initialized
