"""
Agent client service for communicating with AgentCore runtime.
Backend only triggers the agent and receives status updates.
Enhanced with health checking and resilience features.
"""
import httpx
import json
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AgentClient:
    """Client for communicating with AgentCore runtime with enhanced resilience."""

    def __init__(self, agent_url: str = "http://localhost:8080"):
        self.agent_url = agent_url
        self.timeout = 30.0
        self.retry_attempts = 3
        self.retry_delay = 2.0
        self.health_check_timeout = 10.0

    def _parse_response(self, response_data: Any) -> Dict[str, Any]:
        """Parse agent response, handling double-encoded JSON strings."""
        # If response is a string, try to parse it as JSON
        if isinstance(response_data, str):
            try:
                return json.loads(response_data)
            except json.JSONDecodeError as e:
                # Try to handle Python dict string (with single quotes)
                try:
                    import ast
                    return ast.literal_eval(response_data)
                except (ValueError, SyntaxError) as ast_error:
                    # Last resort: use eval() for complex Python dict strings
                    # This is safe since the response comes from our controlled agent
                    try:
                        # Clean up non-serializable objects before eval
                        import re

                        cleaned_data = response_data

                        # Remove bound method objects
                        # Replace <bound method ...> with empty string ""
                        cleaned_data = re.sub(r'<bound method [^>]+>', '""', cleaned_data)

                        # Remove other object representations
                        # Replace <...> patterns with empty string ""
                        cleaned_data = re.sub(r'<[^>]+>', '""', cleaned_data)

                        # Use eval() directly - the response is from our own agent
                        # so we can trust it won't contain malicious code
                        result = eval(cleaned_data)

                        if isinstance(result, dict):
                            return result
                        else:
                            raise ValueError("Eval result is not a dictionary")

                    except Exception as eval_error:
                        # Save the problematic response to a file for debugging
                        try:
                            with open("debug_response.txt", "w") as f:
                                f.write(response_data)
                            logger.error("Saved problematic response to debug_response.txt")
                        except Exception:
                            pass

                        # If all approaches failed, provide detailed error info
                        response_preview = response_data[:1000] if isinstance(response_data, str) else str(response_data)[:1000]
                        response_end = response_data[-500:] if isinstance(response_data, str) and len(response_data) > 1000 else ""

                        return {
                            "status": "error",
                            "message": "Invalid JSON response from agent - possible truncation or malformed JSON",
                            "json_error": str(e),
                            "response_length": len(response_data) if isinstance(response_data, str) else "unknown",
                            "response_start": response_preview,
                            "response_end": response_end,
                            "is_likely_truncated": isinstance(response_data, str) and not response_data.strip().endswith('}'),
                            "attempted_fixes": ["json.loads", "ast.literal_eval", "safe_eval"],
                            "ast_error": str(ast_error),
                            "eval_error": str(eval_error)
                        }

        # If it's already a dict, return it
        if isinstance(response_data, dict):
            return response_data

        # Handle None response (common issue we're seeing)
        if response_data is None:
            return {
                "status": "error",
                "message": "Agent returned None response - possible processing failure",
                "error_type": "null_response"
            }

        # For any other type, return an error
        return {
            "status": "error",
            "message": f"Invalid response type from agent: {type(response_data)}",
            "raw_response": str(response_data)[:500]
        }

    async def validate_connection(self) -> Dict[str, Any]:
        """Validate connection to AgentCore runtime."""
        try:
            async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
                # Try to connect to the runtime
                response = await client.get(f"{self.agent_url}/health")
                return {
                    "status": "connected",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else "unknown"
                }
        except httpx.ConnectError:
            return {
                "status": "connection_failed",
                "message": f"Cannot connect to AgentCore at {self.agent_url}",
                "error_type": "connection_error"
            }
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "message": f"Connection to AgentCore timed out after {self.health_check_timeout}s",
                "error_type": "timeout_error"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error validating connection: {str(e)}",
                "error_type": "validation_error"
            }

    async def _make_request_with_retry(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to AgentCore with retry logic."""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.agent_url}/invocations",
                        json=request_data
                    )
                    
                    # Parse and validate response
                    response_data = response.json()
                    
                    # Log response details for debugging
                    if isinstance(response_data, str):
                        logger.debug(f"Received string response of length: {len(response_data)}")
                    else:
                        logger.debug(f"Received response type: {type(response_data)}")
                    
                    parsed_response = self._parse_response(response_data)
                    
                    # If we got a valid response, return it
                    if parsed_response.get("status") != "error" or parsed_response.get("error_type") != "null_response":
                        return parsed_response
                    
                    # If it's a null response, retry
                    logger.warning(f"Received null response on attempt {attempt + 1}, retrying...")
                    last_error = parsed_response
                    
            except httpx.ConnectError as e:
                last_error = {
                    "status": "error",
                    "message": f"Connection failed to AgentCore: {str(e)}",
                    "error_type": "connection_error",
                    "attempt": attempt + 1
                }
                logger.warning(f"Connection failed on attempt {attempt + 1}: {e}")
                
            except httpx.TimeoutException as e:
                last_error = {
                    "status": "error", 
                    "message": f"Request timed out after {self.timeout}s: {str(e)}",
                    "error_type": "timeout_error",
                    "attempt": attempt + 1
                }
                logger.warning(f"Request timed out on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                last_error = {
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "error_type": "unexpected_error",
                    "attempt": attempt + 1
                }
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            
            # Wait before retrying (except on last attempt)
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        # All attempts failed, return the last error
        if last_error:
            last_error["total_attempts"] = self.retry_attempts
            return last_error
        
        return {
            "status": "error",
            "message": "All retry attempts failed with unknown error",
            "total_attempts": self.retry_attempts
        }

    async def start_course_processing(
        self,
        course_url: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Trigger agent to start course processing.

        Args:
            course_url: URL of the course
            user_id: User ID for tracking

        Returns:
            Agent response with session info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "start_course_processing",
                        "course_url": course_url,
                        "user_id": user_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to connect to agent: {str(e)}"
            }

    async def get_processing_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current status of course processing.

        Args:
            session_id: Session ID

        Returns:
            Current processing status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_status",
                        "session_id": session_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get status: {str(e)}"
            }

    async def continue_after_login(self, session_id: str) -> Dict[str, Any]:
        """
        Continue processing after user login.

        Args:
            session_id: Session ID

        Returns:
            Continuation confirmation
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "continue_after_login",
                        "session_id": session_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to continue processing: {str(e)}"
            }

    async def stop_processing(self, session_id: str) -> Dict[str, Any]:
        """
        Stop course processing.

        Args:
            session_id: Session ID

        Returns:
            Stop confirmation
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "stop_processing",
                        "session_id": session_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to stop processing: {str(e)}"
            }

    async def get_dcv_presigned_url(
        self,
        session_id: str,
        mcp_session_id: str
    ) -> Dict[str, Any]:
        """
        Get presigned URL for DCV live view.

        Args:
            session_id: Session ID
            mcp_session_id: MCP browser session ID

        Returns:
            Presigned URL and session info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_dcv_url",
                        "session_id": session_id,
                        "mcp_session_id": mcp_session_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get DCV URL: {str(e)}"
            }

    async def get_saved_courses(
        self,
        user_id: str,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all saved courses for a user.

        Args:
            user_id: User ID
            query: Optional search query for semantic search

        Returns:
            List of courses
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_saved_courses",
                        "user_id": user_id,
                        "query": query
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get saved courses: {str(e)}",
                "courses": []
            }

    async def get_course_details(
        self,
        user_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information for a specific course.

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            Course details with modules
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_course_details",
                        "user_id": user_id,
                        "course_id": course_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get course details: {str(e)}"
            }

    async def start_file_processing(
        self,
        file_paths: list,
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start file processing asynchronously with enhanced error handling.
        Use get_processing_status to poll for progress.

        Args:
            file_paths: List of file paths to process
            user_id: User ID for tracking
            processing_options: Optional processing configuration

        Returns:
            Session info with session_id for polling
        """
        # Validate connection first
        connection_status = await self.validate_connection()
        if connection_status["status"] != "connected":
            return {
                "status": "error",
                "message": f"Cannot start file processing - AgentCore not accessible: {connection_status.get('message', 'Unknown error')}",
                "connection_details": connection_status,
                "recommendations": [
                    "Start AgentCore runtime service",
                    "Check if port 8080 is available",
                    "Verify system dependencies are installed"
                ]
            }

        request_data = {
            "action": "start_file_processing",
            "file_paths": file_paths,
            "user_id": user_id,
            "processing_options": processing_options or {}
        }
        
        result = await self._make_request_with_retry(request_data)
        
        # Add context to the response
        if result.get("status") == "error":
            result["file_paths"] = file_paths
            result["processing_mode"] = "asynchronous"
            
            # Add specific recommendations
            if result.get("error_type") == "null_response":
                result["recommendations"] = [
                    "Check if AgentCore runtime is properly configured",
                    "Verify all required dependencies are installed",
                    "Check AgentCore logs for startup errors"
                ]
        
        return result

    async def process_uploaded_files(
        self,
        file_paths: list,
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None,
        async_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Process uploaded files through AgentCore with enhanced error handling.

        Args:
            file_paths: List of file paths to process
            user_id: User ID for tracking
            processing_options: Optional processing configuration
            async_mode: If True, use async processing with polling (recommended)

        Returns:
            Processing session info or session_id for polling
        """
        # First validate connection
        connection_status = await self.validate_connection()
        if connection_status["status"] != "connected":
            return {
                "status": "error",
                "message": f"Cannot connect to AgentCore: {connection_status.get('message', 'Unknown connection error')}",
                "connection_details": connection_status,
                "recommendations": [
                    "Check if AgentCore runtime is running",
                    "Verify AgentCore is accessible at " + self.agent_url,
                    "Check network connectivity and firewall settings"
                ]
            }

        if async_mode:
            # Use new async method (recommended)
            return await self.start_file_processing(file_paths, user_id, processing_options)

        # Legacy synchronous mode with enhanced error handling
        request_data = {
            "action": "process_uploaded_files",
            "file_paths": file_paths,
            "user_id": user_id,
            "processing_options": processing_options or {},
            "async_mode": False  # Explicitly request sync mode
        }
        
        # Use longer timeout for file processing
        original_timeout = self.timeout
        self.timeout = 300.0  # 5 minutes for file processing
        
        try:
            result = await self._make_request_with_retry(request_data)
            
            # Add helpful context to error responses
            if result.get("status") == "error":
                result["file_paths"] = file_paths
                result["processing_mode"] = "synchronous"
                
                # Add specific recommendations based on error type
                if result.get("error_type") == "connection_error":
                    result["recommendations"] = [
                        "Check if AgentCore runtime is running",
                        "Verify port 8080 is accessible",
                        "Check system resources and restart AgentCore if needed"
                    ]
                elif result.get("error_type") == "timeout_error":
                    result["recommendations"] = [
                        "Try processing fewer files at once",
                        "Use async mode for large files",
                        "Check if files are accessible and not corrupted"
                    ]
                elif result.get("error_type") == "null_response":
                    result["recommendations"] = [
                        "Check AgentCore logs for processing errors",
                        "Verify file paths are accessible",
                        "Try processing files individually to isolate issues"
                    ]
            
            return result
            
        finally:
            # Restore original timeout
            self.timeout = original_timeout

    async def process_direct_links(
        self,
        links: list,
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process direct resource links through AgentCore.

        Args:
            links: List of URLs to process
            user_id: User ID for tracking
            processing_options: Optional processing configuration

        Returns:
            Processing session info
        """
        try:
            # Use longer timeout for link processing (5 minutes)
            link_processing_timeout = 300.0
            async with httpx.AsyncClient(timeout=link_processing_timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "process_direct_links",
                        "links": links,
                        "user_id": user_id,
                        "processing_options": processing_options or {}
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process direct links: {str(e)}"
            }

    async def process_mixed_content(
        self,
        course_url: Optional[str],
        file_paths: Optional[list],
        direct_links: Optional[list],
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process mixed content (URL + files + links) through AgentCore.

        Args:
            course_url: Optional course URL
            file_paths: Optional list of file paths
            direct_links: Optional list of direct links
            user_id: User ID for tracking
            processing_options: Optional processing configuration

        Returns:
            Processing session info
        """
        try:
            # Use longer timeout for mixed content processing (10 minutes)
            mixed_content_timeout = 600.0
            async with httpx.AsyncClient(timeout=mixed_content_timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "process_mixed_content",
                        "course_url": course_url,
                        "file_paths": file_paths,
                        "direct_links": direct_links,
                        "user_id": user_id,
                        "processing_options": processing_options or {}
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process mixed content: {str(e)}"
            }

    async def validate_links(
        self,
        links: list,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Validate and analyze direct links.

        Args:
            links: List of URLs to validate
            user_id: User ID for tracking

        Returns:
            Validation results
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "validate_links",
                        "links": links,
                        "user_id": user_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to validate links: {str(e)}"
            }

    async def generate_training_content(
        self,
        knowledge_base_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate training content (MCQs, questions) from knowledge base.

        Args:
            knowledge_base_id: Knowledge base ID
            user_id: User ID for tracking

        Returns:
            Generated training content
        """
        try:
            # Use longer timeout for training content generation (3 minutes)
            training_timeout = 180.0
            async with httpx.AsyncClient(timeout=training_timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "generate_training_content",
                        "knowledge_base_id": knowledge_base_id,
                        "user_id": user_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate training content: {str(e)}"
            }

    async def generate_mcq_question(
        self,
        knowledge_base_id: str,
        session_id: str,
        questions_answered: int,
        processed_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an MCQ question for training.

        Args:
            knowledge_base_id: Knowledge base ID
            session_id: Training session ID
            questions_answered: Number of questions already answered

        Returns:
            Generated MCQ question
        """
        try:
            payload = {
                "action": "generate_mcq_question",
                "knowledge_base_id": knowledge_base_id,
                "session_id": session_id,
                "questions_answered": questions_answered
            }

            # Include processed_results if provided (for speed - avoids slow memory retrieval)
            if processed_results:
                payload["processed_results"] = processed_results

            # Use longer timeout for AI question generation (Bedrock API can take 30-60s)
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json=payload
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate MCQ question: {str(e)}"
            }

    async def get_learning_content(self, knowledge_base_id: str) -> Dict[str, Any]:
        """
        Get learning content for studying before assessment.

        Args:
            knowledge_base_id: Knowledge base ID

        Returns:
            Learning content with summary, concepts, objectives
        """
        try:
            # Use longer timeout for AI content generation
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_learning_content",
                        "knowledge_base_id": knowledge_base_id
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get learning content: {str(e)}"
            }

    async def generate_learning_content_from_results(
        self,
        knowledge_base_id: str,
        processed_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate learning content directly from stored processing results.

        Args:
            knowledge_base_id: Knowledge base ID
            processed_results: Dict of agent results by type

        Returns:
            Learning content with summary, concepts, objectives
        """
        try:
            # Use longer timeout for AI content generation
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "generate_learning_content_from_results",
                        "knowledge_base_id": knowledge_base_id,
                        "processed_results": processed_results
                    }
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate learning content from results: {str(e)}"
            }

    async def generate_enhanced_question(
        self,
        knowledge_base_id: str,
        session_id: str,
        question_type: str,
        questions_answered: int,
        processed_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an enhanced question (MCQ, open-ended, fill-blank, etc.) for training.

        Args:
            knowledge_base_id: Knowledge base ID
            session_id: Training session ID
            question_type: Type of question to generate
            questions_answered: Number of questions already answered
            processed_results: Optional processed results from knowledge base (avoids file system access)

        Returns:
            Generated question
        """
        try:
            payload = {
                "action": "generate_enhanced_question",
                "knowledge_base_id": knowledge_base_id,
                "session_id": session_id,
                "question_type": question_type,
                "questions_answered": questions_answered
            }

            # Include processed_results if provided
            if processed_results:
                payload["processed_results"] = processed_results

            # Use longer timeout for question generation (Bedrock API can be slow)
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json=payload
                )
                return self._parse_response(response.json())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate enhanced question: {str(e)}"
            }


# Global agent client instance
agent_client = AgentClient()
