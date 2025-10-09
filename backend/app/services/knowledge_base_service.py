"""
Knowledge Base Service for creating and managing course knowledge bases from uploaded files.
Handles multi-agent processing and training interface.
"""
import uuid
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel
import asyncio
from pathlib import Path

from app.services.agent_client import agent_client
from app.services.file_upload_service import file_upload_service


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    TRAINING = "training"
    COMPLETED = "completed"
    ERROR = "error"


class AgentType(str, Enum):
    TEXT = "text"
    PDF = "pdf"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"


class AgentStatus(BaseModel):
    agent_type: AgentType
    status: ProcessingStatus
    progress: int = 0
    files_processed: int = 0
    total_files: int = 0
    file_ids: List[str] = []  # Track file IDs for cleanup
    error_message: Optional[str] = None
    completed_at: Optional[str] = None


class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    status: ProcessingStatus
    total_files: int
    processed_files: int
    agent_statuses: List[AgentStatus]
    training_ready: bool = False
    session_id: Optional[str] = None
    training_content: Optional[Dict[str, Any]] = None
    processed_results: Optional[Dict[str, Any]] = None  # Store agent processing results


class TrainingSession(BaseModel):
    id: str
    knowledge_base_id: str
    user_id: str
    created_at: str
    status: str = "active"
    current_question: Optional[Dict[str, Any]] = None
    questions_answered: int = 0
    correct_answers: int = 0
    score: float = 0.0
    # Configuration
    question_types: List[str] = ["mcq", "open_ended"]
    question_count: int = 10
    study_time: int = 0


class KnowledgeBaseService:
    """Service for managing knowledge bases and training sessions using AgentCore Memory."""
    
    def __init__(self):
        # Use AgentCore Memory for persistence instead of local storage
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self.training_sessions: Dict[str, TrainingSession] = {}
        self.memory_manager = None
        self.memory = None
        
        # Load existing knowledge bases from AgentCore Memory on startup
        asyncio.create_task(self._load_from_memory())
    
    async def create_knowledge_base(
        self,
        name: str,
        file_paths: List[str],
        user_id: str,
        description: Optional[str] = None
    ) -> KnowledgeBase:
        """Create a new knowledge base from uploaded files."""
        
        kb_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Categorize files by type
        file_categories = self._categorize_files(file_paths)
        
        # Initialize agent statuses and collect file IDs
        agent_statuses = []
        from app.services.file_upload_service import file_upload_service

        for agent_type, files in file_categories.items():
            if files:  # Only create status for agents that have files to process
                # Extract file IDs from file paths
                file_ids = []
                for file_path in files:
                    # Try to find file ID from registry by path
                    for fid, finfo in file_upload_service._file_registry.items():
                        if finfo.file_path == file_path or finfo.upload_path == file_path:
                            file_ids.append(fid)
                            break

                agent_statuses.append(AgentStatus(
                    agent_type=agent_type,
                    status=ProcessingStatus.PENDING,
                    total_files=len(files),
                    file_ids=file_ids
                ))
        
        # Create knowledge base
        kb = KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            status=ProcessingStatus.PROCESSING,
            total_files=len(file_paths),
            processed_files=0,
            agent_statuses=agent_statuses
        )
        
        self.knowledge_bases[kb_id] = kb
        
        # Save to AgentCore Memory
        await self._save_to_memory()
        
        # Start processing in background
        asyncio.create_task(self._process_knowledge_base(kb_id, file_categories, user_id))
        
        return kb
    
    def _categorize_files(self, file_paths: List[str]) -> Dict[AgentType, List[str]]:
        """Categorize files by type for different agents."""
        categories = {
            AgentType.TEXT: [],
            AgentType.PDF: [],
            AgentType.AUDIO: [],
            AgentType.VIDEO: [],
            AgentType.IMAGE: []
        }
        
        for file_path in file_paths:
            file_lower = file_path.lower()
            
            # Extract just the filename if it's a full path
            filename = os.path.basename(file_path).lower()
            
            # Check by file extension
            if filename.endswith('.pdf'):
                categories[AgentType.PDF].append(file_path)
            elif filename.endswith(('.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg')):
                categories[AgentType.AUDIO].append(file_path)
            elif filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v')):
                categories[AgentType.VIDEO].append(file_path)
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg')):
                categories[AgentType.IMAGE].append(file_path)
            elif filename.endswith(('.txt', '.docx', '.doc', '.pptx', '.ppt', '.rtf', '.odt')):
                categories[AgentType.TEXT].append(file_path)
            # Check by path structure (for uploaded files)
            elif '/video/' in file_lower or '\\video\\' in file_lower:
                categories[AgentType.VIDEO].append(file_path)
            elif '/audio/' in file_lower or '\\audio\\' in file_lower:
                categories[AgentType.AUDIO].append(file_path)
            elif '/image/' in file_lower or '\\image\\' in file_lower:
                categories[AgentType.IMAGE].append(file_path)
            elif '/document/' in file_lower or '\\document\\' in file_lower:
                # Check if it's a PDF in document folder
                if 'pdf' in filename:
                    categories[AgentType.PDF].append(file_path)
                else:
                    categories[AgentType.TEXT].append(file_path)
            else:
                # Default to text processing
                categories[AgentType.TEXT].append(file_path)
                print(f"⚠️ Unknown file type for {file_path}, defaulting to text processing")
        
        return categories
    
    async def _process_knowledge_base(
        self,
        kb_id: str,
        file_categories: Dict[AgentType, List[str]],
        user_id: str
    ):
        """Process knowledge base with multiple agents."""
        try:
            kb = self.knowledge_bases[kb_id]
            
            # Process each category with its respective agent
            processing_tasks = []
            
            for agent_type, files in file_categories.items():
                if files:
                    task = self._process_agent_files(kb_id, agent_type, files, user_id)
                    processing_tasks.append(task)
            
            # Wait for all agents to complete
            await asyncio.gather(*processing_tasks)
            
            # Check if any agents failed
            failed_agents = [agent for agent in kb.agent_statuses if agent.status == ProcessingStatus.ERROR]
            if failed_agents:
                kb.status = ProcessingStatus.ERROR
                kb.updated_at = datetime.now().isoformat()
                error_messages = [f"{agent.agent_type}: {agent.error_message}" for agent in failed_agents]
                print(f"❌ KB {kb_id} processing failed. Errors: {'; '.join(error_messages)}")
                return
            
            # All agents completed successfully, start training phase
            print(f"🔄 All agents completed for KB {kb_id}, starting training content generation...")
            kb.status = ProcessingStatus.TRAINING
            kb.updated_at = datetime.now().isoformat()

            # Generate training content
            await self._generate_training_content(kb_id, user_id)

            # Check if training content was successfully generated before marking ready
            kb = self.knowledge_bases[kb_id]
            if kb.training_content and kb.training_content.get("status") == "completed":
                # Mark as completed and training ready ONLY if content generation succeeded
                print(f"✅ Knowledge base {kb_id} is now ready for training!")
                kb.status = ProcessingStatus.COMPLETED
                kb.training_ready = True
                kb.updated_at = datetime.now().isoformat()
            else:
                # Training content generation failed or incomplete
                print(f"⚠️ Training content generation incomplete for KB {kb_id}")
                kb.status = ProcessingStatus.COMPLETED  # File processing completed
                kb.training_ready = False  # But not ready for training yet
                kb.updated_at = datetime.now().isoformat()
                print(f"💡 Training content can be regenerated manually via /generate-training endpoint")

            # Save updated status to AgentCore Memory
            await self._save_to_memory()

            # Clean up uploaded files after successful processing
            await self._cleanup_uploaded_files(kb_id, user_id)
            
        except Exception as e:
            kb = self.knowledge_bases[kb_id]
            kb.status = ProcessingStatus.ERROR
            kb.updated_at = datetime.now().isoformat()
            print(f"Error processing knowledge base {kb_id}: {e}")
    
    async def _process_agent_files(
        self,
        kb_id: str,
        agent_type: AgentType,
        files: List[str],
        user_id: str
    ):
        """Process files with a specific agent type using async AgentCore processing."""
        try:
            kb = self.knowledge_bases[kb_id]

            # Find the agent status
            agent_status = None
            for status in kb.agent_statuses:
                if status.agent_type == agent_type:
                    agent_status = status
                    break

            if not agent_status:
                return

            # Update status to processing
            agent_status.status = ProcessingStatus.PROCESSING
            print(f"🔄 Starting {agent_type.value} agent processing for {len(files)} files...")

            # Start async processing (returns immediately with session_id)
            result = await agent_client.process_uploaded_files(
                file_paths=files,
                user_id=user_id,
                processing_options={
                    "agent_type": agent_type.value,
                    "knowledge_base_id": kb_id,
                    "batch_processing": True
                },
                async_mode=True  # Use async mode
            )

            # Get session_id for polling
            session_id = result.get("session_id")
            if not session_id:
                # Fallback to sync mode if no session_id returned
                agent_status.status = ProcessingStatus.ERROR
                agent_status.error_message = result.get("message", "Failed to start processing")
                print(f"❌ {agent_type.value} agent failed to start: {result.get('message')}")
                return

            print(f"📊 {agent_type.value} agent started with session {session_id}, polling for status...")

            # Poll for status until completed or error
            max_poll_attempts = 600  # 10 minutes max (1 poll every second)
            poll_interval = 1  # seconds

            for attempt in range(max_poll_attempts):
                await asyncio.sleep(poll_interval)

                # Get processing status
                status_result = await agent_client.get_processing_status(session_id)

                # Ensure status_result is a dict
                if not isinstance(status_result, dict):
                    print(f"⚠️ Unexpected status result type: {type(status_result)} - {status_result}")
                    agent_status.status = ProcessingStatus.ERROR
                    agent_status.error_message = f"Invalid status response: {status_result}"
                    return

                if status_result.get("status") == "not_found":
                    agent_status.status = ProcessingStatus.ERROR
                    agent_status.error_message = "Session not found"
                    print(f"❌ Session {session_id} not found")
                    return

                current_status = status_result.get("status")
                progress = status_result.get("progress", 0)

                # Update agent status
                agent_status.progress = progress

                if current_status == "completed":
                    # Processing completed successfully
                    agent_status.files_processed = len(files)
                    agent_status.progress = 100
                    agent_status.status = ProcessingStatus.COMPLETED
                    agent_status.completed_at = datetime.now().isoformat()

                    # **CRITICAL FIX**: Store the actual processing results!
                    if "results" in status_result:
                        if kb.processed_results is None:
                            kb.processed_results = {}
                        kb.processed_results[agent_type.value] = status_result["results"]
                        print(f"💾 Stored {len(status_result['results'])} results from {agent_type.value} agent")

                    print(f"✅ {agent_type.value} agent completed processing {len(files)} files")
                    break

                elif current_status == "error":
                    # Processing failed
                    agent_status.status = ProcessingStatus.ERROR
                    error_msg = status_result.get("error") or status_result.get("message") or "Processing failed"
                    agent_status.error_message = error_msg
                    print(f"❌ {agent_type.value} agent failed: {error_msg}")
                    print(f"   Full error response: {status_result}")
                    break

                # Log progress periodically
                if attempt % 10 == 0:
                    print(f"  📈 {agent_type.value} agent progress: {progress}%")

            # Check if we timed out
            if agent_status.status == ProcessingStatus.PROCESSING:
                agent_status.status = ProcessingStatus.ERROR
                agent_status.error_message = f"Processing timeout after {max_poll_attempts} seconds"
                print(f"⏱️ {agent_type.value} agent timeout after {max_poll_attempts}s")

            # Update overall KB progress
            total_processed = sum(status.files_processed for status in kb.agent_statuses)
            kb.processed_files = total_processed
            kb.updated_at = datetime.now().isoformat()

        except Exception as e:
            if agent_status:
                agent_status.status = ProcessingStatus.ERROR
                agent_status.error_message = str(e)
            print(f"❌ Error in {agent_type} agent: {e}")
    
    async def _generate_training_content(self, kb_id: str, user_id: str):
        """Generate training content (MCQs, questions) from processed knowledge base with retry logic."""
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                print(f"🧠 Generating training content for KB {kb_id} (attempt {attempt + 1}/{max_attempts})...")
                
                # Add progressive delay between attempts
                if attempt > 0:
                    delay = min(60, 15 * attempt)  # 15s, 30s, 45s, 60s
                    print(f"⏳ Waiting {delay}s before retry to avoid throttling...")
                    await asyncio.sleep(delay)
                
                # Call the real agent to generate training content from AgentCore Memory
                result = await agent_client.generate_training_content(
                    knowledge_base_id=kb_id,
                    user_id=user_id
                )
                
                # Store training content in the knowledge base
                kb = self.knowledge_bases[kb_id]
                if result.get("status") == "completed":
                    kb.training_content = result
                    print(f"✅ Training content generated successfully for KB {kb_id} on attempt {attempt + 1}")
                    return  # Success, exit retry loop
                elif "ThrottlingException" in str(result.get("message", "")) or "Too many requests" in str(result.get("message", "")):
                    print(f"⚠️ Throttled on attempt {attempt + 1}, will retry...")
                    if attempt == max_attempts - 1:
                        print(f"❌ Failed to generate training content after {max_attempts} attempts due to throttling")
                        kb.training_content = {"status": "error", "message": "Training content generation failed due to rate limiting"}
                    continue
                else:
                    print(f"⚠️ Training content generation had issues: {result.get('message')}")
                    kb.training_content = result
                    return  # Non-throttling error, don't retry
                
            except Exception as e:
                if "ThrottlingException" in str(e) or "Too many requests" in str(e):
                    print(f"⚠️ Throttling exception on attempt {attempt + 1}: {e}")
                    if attempt == max_attempts - 1:
                        print(f"❌ Failed to generate training content after {max_attempts} attempts")
                        kb = self.knowledge_bases[kb_id]
                        kb.training_content = {"status": "error", "message": f"Training content generation failed after {max_attempts} attempts due to throttling"}
                    continue
                else:
                    print(f"❌ Error generating training content for KB {kb_id}: {e}")
                    kb = self.knowledge_bases[kb_id]
                    kb.training_content = {"status": "error", "message": str(e)}
                    return  # Non-throttling error, don't retry
    
    def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get knowledge base by ID."""
        return self.knowledge_bases.get(kb_id)
    
    def list_knowledge_bases(self, user_id: str) -> List[KnowledgeBase]:
        """List all knowledge bases for a user."""
        # In production, filter by user_id from database
        return list(self.knowledge_bases.values())
    
    async def get_learning_content(self, kb_id: str) -> Dict[str, Any]:
        """Get learning content for studying before assessment."""
        kb = self.knowledge_bases.get(kb_id)
        if not kb:
            raise ValueError("Knowledge base not found")

        try:
            # **PRIORITY 1**: Extract from training_content if available
            if kb.training_content:
                print(f"✅ Found training_content for KB {kb_id}, extracting...")
                extracted_content = self._extract_from_training_content(kb.training_content)
                if extracted_content:
                    print(f"✅ Successfully extracted content from training_content")
                    return extracted_content

            # **PRIORITY 2**: Use stored processed_results
            if kb.processed_results:
                print(f"✅ Found stored processing results for KB {kb_id}")
                print(f"   Agent types: {list(kb.processed_results.keys())}")

                # Generate learning content from stored results
                result = await agent_client.generate_learning_content_from_results(kb_id, kb.processed_results)

                if result.get("status") == "completed" and result.get("content"):
                    print(f"✅ Generated AI learning content from stored results")
                    return result["content"]
                else:
                    print(f"⚠️ Could not generate from results: {result.get('message')}")
            else:
                print(f"⚠️ No processed_results found in KB, trying agent memory search...")

                # Fallback: Try agent memory search
                result = await agent_client.get_learning_content(kb_id)

                if result.get("status") == "completed" and result.get("content"):
                    print(f"✅ Using AI-generated learning content from memory")
                    return result["content"]
                else:
                    print(f"⚠️ Memory search failed: {result.get('message')}")

            # Final fallback
            print(f"⚠️ Using fallback learning content")
            return self._generate_fallback_learning_content(kb)

        except Exception as e:
            print(f"❌ Error getting learning content for KB {kb_id}: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_fallback_learning_content(kb)
    
    def _extract_from_training_content(self, training_content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract learning content from training_content field."""
        try:
            import re
            content_str = training_content.get('training_content', '')

            if not content_str:
                return None

            # Find JSON object in the string
            json_match = re.search(r'\{[\s\S]*\}', content_str)
            if not json_match:
                return None

            parsed = json.loads(json_match.group(0))

            # Extract and format key concepts
            key_concepts = []
            for concept in parsed.get('key_concepts', []):
                if isinstance(concept, dict):
                    key_concepts.append(concept.get('term', ''))
                else:
                    key_concepts.append(str(concept))

            # Get learning objectives
            learning_objectives = parsed.get('learning_objectives', [])

            # Create summary from content_summary
            summary = parsed.get('content_summary', '')

            if not summary:
                summary = f"This course covers {', '.join(parsed.get('topic_areas', [])[:3])}"

            return {
                "summary": summary,
                "key_concepts": key_concepts[:10],  # Limit to 10
                "learning_objectives": learning_objectives[:7]  # Limit to 7
            }
        except Exception as e:
            print(f"⚠️ Failed to extract from training_content: {e}")
            return None

    def _generate_fallback_learning_content(self, kb: KnowledgeBase) -> Dict[str, Any]:
        """Generate fallback learning content when agent is not available."""
        return {
            "summary": f"This course covers the key concepts and materials from {kb.name}. "
                      f"The content has been processed from {kb.total_files} files and is ready for interactive learning.",
            "key_concepts": [
                "Fundamental principles and definitions",
                "Core methodologies and approaches",
                "Practical applications and examples",
                "Advanced topics and considerations",
                "Best practices and common patterns"
            ],
            "learning_objectives": [
                f"Understand the main concepts presented in {kb.name}",
                "Apply learned principles to solve problems",
                "Analyze relationships between different topics",
                "Evaluate different approaches and methods",
                "Create solutions using the acquired knowledge"
            ]
        }

    async def start_training_session(
        self,
        kb_id: str,
        user_id: str,
        question_types: Optional[List[str]] = None,
        question_count: Optional[int] = None,
        study_time: Optional[int] = None
    ) -> TrainingSession:
        """Start a new training session for a knowledge base."""
        
        kb = self.knowledge_bases.get(kb_id)
        if not kb or not kb.training_ready:
            raise ValueError("Knowledge base not ready for training")
        
        session_id = str(uuid.uuid4())
        
        session = TrainingSession(
            id=session_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            question_types=question_types or ["mcq", "open_ended"],
            question_count=question_count or 10,
            study_time=study_time or 0
        )

        self.training_sessions[session_id] = session
        
        # Generate first question
        print(f"🎯 Starting training session {session_id} for KB {kb_id}")
        await self._generate_next_question(session_id)
        
        # Ensure we have a question before returning
        if not session.current_question:
            print(f"⚠️ No question generated, creating fallback for session {session_id}")
            session.current_question = self._generate_fallback_question(0, kb.name)
        
        # Save session to persistent storage
        await self._save_to_memory()
        
        return session
    
    async def _generate_next_question(self, session_id: str):
        """Generate the next question for a training session."""
        try:
            session = self.training_sessions[session_id]
            kb = self.knowledge_bases[session.knowledge_base_id]

            # Determine which question type to generate (cycle through configured types)
            question_type = session.question_types[session.questions_answered % len(session.question_types)]

            print(f"🧠 Generating question {session.questions_answered + 1} for session {session_id}")
            print(f"📚 Knowledge base: {kb.name} (ID: {kb.id})")
            print(f"❓ Question type: {question_type}")

            # Add small delay to prevent Bedrock API throttling
            if session.questions_answered > 0:
                import asyncio
                await asyncio.sleep(1.5)  # 1.5 second delay between questions

            # Debug: Check what we're sending
            print(f"🔍 KB has processed_results: {bool(kb.processed_results)}")
            if kb.processed_results:
                print(f"   Keys in processed_results: {list(kb.processed_results.keys())}")

            # Call agent to generate question of the specified type
            # Pass processed_results so agent can access educational content directly
            result = await agent_client.generate_enhanced_question(
                knowledge_base_id=kb.id,
                session_id=session_id,
                question_type=question_type,
                questions_answered=session.questions_answered,
                processed_results=kb.processed_results
            )
            
            # Validate the result and question structure
            if (result.get("status") == "completed" and 
                result.get("question") and 
                self._validate_question_structure(result.get("question"))):
                session.current_question = result.get("question")
                print(f"✅ Question generated successfully for session {session_id}")
                print(f"🎯 Question topic: {session.current_question.get('topic', 'General Knowledge')}")
            else:
                print(f"⚠️ Agent failed to generate valid question: {result.get('message', 'Unknown error')}")
                print(f"🔄 Using contextual fallback for session {session_id}")
                # Fallback question when agent is not available or returns invalid data
                session.current_question = self._generate_fallback_question(session.questions_answered, kb.name)
            
        except Exception as e:
            print(f"❌ Error generating question for session {session_id}: {e}")
            # Provide fallback question
            session = self.training_sessions.get(session_id)
            if session:
                kb = self.knowledge_bases.get(session.knowledge_base_id)
                kb_name = kb.name if kb else "Unknown Course"
                session.current_question = self._generate_fallback_question(session.questions_answered, kb_name)
                print(f"🔄 Using fallback question for session {session_id}")
    
    def _validate_question_structure(self, question: Dict[str, Any]) -> bool:
        """Validate that a question has all required fields with proper types."""
        try:
            required_fields = ['question', 'options', 'correct_answer', 'explanation']
            
            # Check all required fields exist and are not None/empty
            for field in required_fields:
                if not question.get(field):
                    print(f"⚠️ Question validation failed: missing or empty field '{field}'")
                    return False
            
            # Validate question text is a string
            if not isinstance(question.get('question'), str):
                print(f"⚠️ Question validation failed: 'question' field is not a string")
                return False
            
            # Validate options is a dict with string values
            options = question.get('options')
            if not isinstance(options, dict) or len(options) < 2:
                print(f"⚠️ Question validation failed: 'options' must be a dict with at least 2 options")
                return False
            
            for key, value in options.items():
                if not isinstance(value, str):
                    print(f"⚠️ Question validation failed: option '{key}' value is not a string")
                    return False
            
            # Validate correct_answer exists in options
            correct_answer = question.get('correct_answer')
            if correct_answer not in options:
                print(f"⚠️ Question validation failed: correct_answer '{correct_answer}' not found in options")
                return False
            
            # Validate explanation is a string
            if not isinstance(question.get('explanation'), str):
                print(f"⚠️ Question validation failed: 'explanation' field is not a string")
                return False
            
            print(f"✅ Question structure validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Question validation error: {e}")
            return False
    
    def _generate_fallback_question(self, question_number: int, kb_name: str) -> Dict[str, Any]:
        """Generate a contextual fallback question when the agent is not available."""

        try:
            # Ensure kb_name is a valid string
            if not kb_name or not isinstance(kb_name, str):
                kb_name = "Unknown Course"

            # Try to infer subject matter from knowledge base name
            kb_name_lower = kb_name.lower()

            # Programming-related fallback questions
            if any(term in kb_name_lower for term in ['program', 'code', 'java', 'python', 'c++', 'javascript', 'programming']):
                programming_questions = [
                {
                    "type": "mcq",
                    "question": f"In {kb_name}, what is typically the first concept beginners should master?",
                    "options": {
                        "A": "Advanced algorithms and data structures",
                        "B": "Basic syntax and variable declarations",
                        "C": "Object-oriented programming principles",
                        "D": "Database integration techniques"
                    },
                    "correct_answer": "B",
                    "explanation": "Programming education typically starts with basic syntax, variables, and fundamental concepts before moving to more complex topics.",
                    "difficulty": "beginner",
                    "topic": "Programming Fundamentals",
                    "learning_objective": "Understand the foundational elements of programming"
                },
                {
                    "type": "mcq",
                    "question": f"When learning {kb_name}, what is the most effective way to practice?",
                    "options": {
                        "A": "Only reading theory without coding",
                        "B": "Writing and testing small programs regularly",
                        "C": "Memorizing syntax without understanding",
                        "D": "Copying code without modification"
                    },
                    "correct_answer": "B",
                    "explanation": "Active practice through writing and testing code is essential for developing programming skills and understanding concepts.",
                    "difficulty": "intermediate",
                    "topic": "Learning Methodology",
                    "learning_objective": "Apply effective learning strategies for programming"
                },
                {
                    "type": "mcq",
                    "question": f"What is a key principle when writing code in {kb_name}?",
                    "options": {
                        "A": "Write code as quickly as possible",
                        "B": "Make code as complex as possible",
                        "C": "Write clear, readable, and maintainable code",
                        "D": "Avoid using comments or documentation"
                    },
                    "correct_answer": "C",
                    "explanation": "Good programming practices emphasize writing clear, readable, and maintainable code that others can understand and modify.",
                    "difficulty": "intermediate",
                    "topic": "Code Quality",
                    "learning_objective": "Understand principles of good programming practices"
                }
                ]
                question_index = min(question_number, len(programming_questions) - 1)
                return programming_questions[question_index]

            # General educational fallback questions
            fallback_questions = [
                {
                    "type": "mcq",
                    "question": f"What is the main topic covered in the '{kb_name}' course materials?",
                    "options": {
                        "A": "Basic fundamentals and core concepts",
                        "B": "Advanced theoretical frameworks",
                        "C": "Practical implementation techniques",
                        "D": "Historical background and context"
                    },
                    "correct_answer": "A",
                    "explanation": "Most educational materials start with fundamental concepts before progressing to more advanced topics.",
                    "difficulty": "beginner",
                    "topic": "Course Overview",
                    "learning_objective": "Understand the primary focus of the course content"
                },
                {
                    "type": "mcq",
                    "question": f"Based on the '{kb_name}' materials, what would be the best approach to learning this subject?",
                    "options": {
                        "A": "Memorize all details without understanding",
                        "B": "Focus on practical applications first",
                        "C": "Start with fundamentals and build up gradually",
                        "D": "Skip to advanced topics immediately"
                    },
                    "correct_answer": "C",
                    "explanation": "Effective learning typically follows a progressive approach, building from basic concepts to more complex ideas.",
                    "difficulty": "intermediate",
                    "topic": "Learning Strategy",
                    "learning_objective": "Develop effective learning approaches for the subject matter"
                },
                {
                    "type": "mcq",
                    "question": f"What type of knowledge or skills would you expect to gain from '{kb_name}'?",
                    "options": {
                        "A": "Theoretical knowledge only",
                        "B": "Practical skills only",
                        "C": "A combination of theory and practice",
                        "D": "General awareness without depth"
                    },
                    "correct_answer": "C",
                    "explanation": "Most comprehensive educational materials aim to provide both theoretical understanding and practical application skills.",
                    "difficulty": "intermediate",
                    "topic": "Learning Outcomes",
                    "learning_objective": "Identify expected learning outcomes from the course materials"
                }
            ]

            # Cycle through questions or use the last one for higher numbers
            question_index = min(question_number, len(fallback_questions) - 1)
            question = fallback_questions[question_index]

            # Validate the fallback question structure before returning
            if self._validate_question_structure(question):
                return question
            else:
                # If validation fails, return a guaranteed safe question
                return self._get_emergency_fallback_question(kb_name)

        except Exception as e:
            print(f"❌ Error in fallback question generation: {e}")
            # Return emergency fallback question
            return self._get_emergency_fallback_question(kb_name)
    
    def _get_emergency_fallback_question(self, kb_name: str) -> Dict[str, Any]:
        """Generate an emergency fallback question that is guaranteed to be valid."""
        return {
            "type": "mcq",
            "question": f"What is your primary goal when studying {kb_name}?",
            "options": {
                "A": "To understand the basic concepts",
                "B": "To memorize all details",
                "C": "To skip difficult topics",
                "D": "To finish as quickly as possible"
            },
            "correct_answer": "A",
            "explanation": "Understanding basic concepts provides a solid foundation for learning any subject effectively.",
            "difficulty": "beginner",
            "topic": "Learning Goals",
            "learning_objective": "Establish effective learning objectives"
        }
    
    async def answer_question(
        self,
        session_id: str,
        answer: str
    ) -> Dict[str, Any]:
        """Process an answer to a training question."""
        
        session = self.training_sessions.get(session_id)
        if not session or not session.current_question:
            raise ValueError("Invalid session or no current question")
        
        # Check if answer is correct
        correct_answer = session.current_question.get("correct_answer")
        is_correct = answer.lower() == correct_answer.lower()
        
        # Update session stats
        session.questions_answered += 1
        if is_correct:
            session.correct_answers += 1
        
        session.score = (session.correct_answers / session.questions_answered) * 100
        
        # Generate next question
        await self._generate_next_question(session_id)
        
        # Save updated session to persistent storage
        await self._save_to_memory()
        
        return {
            "correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": session.current_question.get("explanation", ""),
            "score": session.score,
            "questions_answered": session.questions_answered,
            "next_question": session.current_question
        }
    
    def get_training_session(self, session_id: str) -> Optional[TrainingSession]:
        """Get training session by ID."""
        return self.training_sessions.get(session_id)
    
    def get_user_training_history(self, user_id: str) -> List[TrainingSession]:
        """Get all training sessions for a user."""
        return [
            session for session in self.training_sessions.values()
            if session.user_id == user_id
        ]
    
    def get_knowledge_base_training_history(self, kb_id: str) -> List[TrainingSession]:
        """Get all training sessions for a specific knowledge base."""
        return [
            session for session in self.training_sessions.values()
            if session.knowledge_base_id == kb_id
        ]
    
    def get_training_sessions_count_for_kb(self, kb_id: str) -> int:
        """Get count of training sessions for a specific knowledge base."""
        return len([
            session for session in self.training_sessions.values()
            if session.knowledge_base_id == kb_id
        ])
    
    def verify_kb_cleanup(self, kb_id: str) -> Dict[str, Any]:
        """Verify that a knowledge base and its training sessions have been properly cleaned up."""
        kb_exists = kb_id in self.knowledge_bases
        session_count = self.get_training_sessions_count_for_kb(kb_id)
        
        return {
            "knowledge_base_exists": kb_exists,
            "training_sessions_count": session_count,
            "cleanup_complete": not kb_exists and session_count == 0
        }
    
    async def recategorize_knowledge_base(self, kb_id: str, correct_file_paths: List[str]) -> Dict[str, Any]:
        """Recategorize a knowledge base with correct file paths/types."""
        try:
            kb = self.knowledge_bases.get(kb_id)
            if not kb:
                return {"status": "error", "message": "Knowledge base not found"}
            
            print(f"🔄 Recategorizing knowledge base {kb_id} with correct file paths")
            
            # Recategorize files with correct paths
            file_categories = self._categorize_files(correct_file_paths)
            
            # Update agent statuses based on new categorization
            new_agent_statuses = []
            for agent_type, files in file_categories.items():
                if files:
                    new_agent_statuses.append(AgentStatus(
                        agent_type=agent_type,
                        status=ProcessingStatus.COMPLETED,  # Mark as completed since processing was done
                        total_files=len(files),
                        files_processed=len(files),
                        progress=100,
                        completed_at=datetime.now().isoformat()
                    ))
            
            # Update knowledge base
            kb.agent_statuses = new_agent_statuses
            kb.updated_at = datetime.now().isoformat()
            
            # Save changes
            await self._save_to_memory()
            
            print(f"✅ Successfully recategorized knowledge base {kb_id}")
            print(f"   New agent types: {[status.agent_type for status in new_agent_statuses]}")
            
            return {
                "status": "success",
                "message": "Knowledge base recategorized successfully",
                "agent_types": [status.agent_type for status in new_agent_statuses]
            }
            
        except Exception as e:
            print(f"❌ Error recategorizing knowledge base {kb_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def end_training_session(self, session_id: str) -> Dict[str, Any]:
        """End a training session and return final results."""
        
        session = self.training_sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        session.status = "completed"
        
        # Save completed session to persistent storage
        await self._save_to_memory()
        
        return {
            "session_id": session_id,
            "final_score": session.score,
            "questions_answered": session.questions_answered,
            "correct_answers": session.correct_answers,
            "accuracy": (session.correct_answers / session.questions_answered * 100) if session.questions_answered > 0 else 0
        }
    
    async def delete_knowledge_base(self, kb_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a knowledge base and clean up associated data."""
        try:
            kb = self.knowledge_bases.get(kb_id)
            if not kb:
                return {
                    "status": "error",
                    "message": "Knowledge base not found"
                }
            
            print(f"🗑️ Deleting knowledge base {kb_id} for user {user_id}")
            
            # Clean up AgentCore Memory if available
            await self._cleanup_kb_memory(kb_id, user_id)

            # Clean up uploaded files
            await self._cleanup_uploaded_files(kb_id, user_id)

            # Clean up any associated training sessions FIRST
            sessions_to_remove = [
                session_id for session_id, session in self.training_sessions.items()
                if session.knowledge_base_id == kb_id
            ]
            
            if sessions_to_remove:
                print(f"🗑️ Found {len(sessions_to_remove)} training sessions to delete for KB {kb_id}")
                for session_id in sessions_to_remove:
                    session = self.training_sessions[session_id]
                    print(f"   - Deleting session {session_id} (created: {session.created_at}, status: {session.status})")
                    del self.training_sessions[session_id]
                print(f"✅ Cleaned up {len(sessions_to_remove)} training sessions for KB {kb_id}")
            else:
                print(f"ℹ️ No training sessions found for KB {kb_id}")
            
            # Remove from local storage
            del self.knowledge_bases[kb_id]
            
            # Save updated registry and sessions to persistent storage
            await self._save_to_memory()
            
            print(f"✅ Successfully deleted knowledge base {kb_id}")
            
            return {
                "status": "success",
                "message": "Knowledge base deleted successfully",
                "deleted_sessions": len(sessions_to_remove)
            }
            
        except Exception as e:
            print(f"❌ Error deleting knowledge base {kb_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to delete knowledge base: {str(e)}"
            }
    
    async def _cleanup_kb_memory(self, kb_id: str, user_id: str):
        """Clean up AgentCore Memory sessions for a knowledge base."""
        try:
            # This would clean up memory sessions in a real implementation
            # For now, we'll just log the cleanup
            agent_types = ["pdf", "video", "audio", "image", "text"]
            memory_sessions = []
            
            for agent_type in agent_types:
                memory_sessions.extend([
                    f"{kb_id}_{agent_type}",
                    f"{kb_id}_{agent_type}_analysis"
                ])
            
            memory_sessions.append(f"{kb_id}_training_content")
            
            print(f"🧹 Cleaning up {len(memory_sessions)} memory sessions for KB {kb_id}")
            
            # In a real implementation, you would call AgentCore Memory API to delete these sessions
            # For now, we'll just log what would be deleted
            for session_id in memory_sessions:
                print(f"   - Would delete memory session: {session_id}")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up memory for KB {kb_id}: {e}")

    async def _cleanup_uploaded_files(self, kb_id: str, user_id: str):
        """Clean up uploaded files after successful processing."""
        try:
            kb = self.knowledge_bases.get(kb_id)
            if not kb:
                return

            deleted_count = 0
            total_size = 0

            # Get all file IDs from the knowledge base
            file_ids = []
            for agent_status in kb.agent_statuses:
                if agent_status.file_ids:
                    file_ids.extend(agent_status.file_ids)

            print(f"🧹 Cleaning up {len(file_ids)} uploaded files for KB {kb_id}...")

            # Delete each file
            for file_id in file_ids:
                file_info = file_upload_service.get_file_info(file_id)
                if file_info:
                    # Track file size before deletion
                    total_size += file_info.file_size

                    # Delete the file
                    if file_upload_service.delete_file(file_id, user_id):
                        deleted_count += 1

            # Convert size to human-readable format
            size_mb = total_size / (1024 * 1024)
            if deleted_count > 0:
                print(f"✅ Cleaned up {deleted_count} files ({size_mb:.2f} MB) for KB {kb_id}")
            else:
                print(f"ℹ️ No files to clean up for KB {kb_id}")

        except Exception as e:
            print(f"⚠️ Warning: Could not clean up files for KB {kb_id}: {e}")

    def _init_memory(self):
        """Initialize AgentCore Memory for knowledge base persistence."""
        # Memory operations are handled by the agent, not the backend
        # The backend will use simple file-based persistence as fallback
        print("ℹ️ Knowledge Base persistence will be handled by AgentCore agent")
        return None

    async def _load_from_memory(self):
        """Load existing knowledge bases and training sessions from simple file storage."""
        try:
            # Load knowledge bases
            kb_file = Path("data/knowledge_bases.json")
            if kb_file.exists():
                with open(kb_file, 'r') as f:
                    kb_data = json.load(f)
                    for kb_id, kb_dict in kb_data.items():
                        # Reconstruct KnowledgeBase objects
                        kb = KnowledgeBase(**kb_dict)
                        self.knowledge_bases[kb_id] = kb
                    
                    print(f"✅ Loaded {len(self.knowledge_bases)} knowledge bases from file storage")
            else:
                print("ℹ️ No existing knowledge base registry found, starting fresh")
            
            # Load training sessions
            sessions_file = Path("data/training_sessions.json")
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    session_data = json.load(f)
                    for session_id, session_dict in session_data.items():
                        # Reconstruct TrainingSession objects
                        session = TrainingSession(**session_dict)
                        self.training_sessions[session_id] = session
                    
                    print(f"✅ Loaded {len(self.training_sessions)} training sessions from file storage")
            else:
                print("ℹ️ No existing training sessions found, starting fresh")
                
        except Exception as e:
            print(f"❌ Error loading data: {e}")

    async def _save_to_memory(self):
        """Save knowledge bases and training sessions to simple file storage."""
        try:
            # Create data directory if it doesn't exist
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            # Convert knowledge bases to serializable format
            kb_data = {}
            for kb_id, kb in self.knowledge_bases.items():
                kb_data[kb_id] = kb.dict()
            
            # Save knowledge bases to file
            kb_file = data_dir / "knowledge_bases.json"
            with open(kb_file, 'w') as f:
                json.dump(kb_data, f, indent=2)
            
            # Convert training sessions to serializable format
            session_data = {}
            for session_id, session in self.training_sessions.items():
                session_data[session_id] = session.dict()
            
            # Save training sessions to file
            sessions_file = data_dir / "training_sessions.json"
            with open(sessions_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            print(f"✅ Saved {len(self.knowledge_bases)} knowledge bases and {len(self.training_sessions)} training sessions to file storage")
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")


# Global service instance
knowledge_base_service = KnowledgeBaseService()