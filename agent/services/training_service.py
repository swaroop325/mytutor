"""
Training Service - Service layer for integrating training agent with the system
Handles training content generation, assessment creation, and MCQ generation
"""
import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from agents.training_agent import TrainingAgent, AssessmentSet

logger = logging.getLogger(__name__)


class TrainingService:
    """Service for managing training content generation and assessments."""
    
    def __init__(self):
        self.training_agent = TrainingAgent()
        logger.info("Training Service initialized")
    
    async def generate_training_content_from_kb(self, kb_id: str, content_data: Dict[str, Any],
                                              training_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate training content from knowledge base content."""
        try:
            logger.info(f"Generating training content for KB: {kb_id}")
            
            # Extract content from different agent results
            combined_content = self._extract_content_from_kb_data(content_data)
            
            if not combined_content.strip():
                return {
                    "status": "error",
                    "message": "No content available for training generation",
                    "training_content": None
                }
            
            # Prepare content metadata
            content_metadata = {
                "kb_id": kb_id,
                "content_type": "knowledge_base",
                "filename": f"KB_{kb_id}",
                "processed_at": datetime.now().isoformat(),
                "source_agents": list(content_data.keys())
            }
            
            # Generate assessment
            assessment = await self.training_agent.generate_assessment(
                combined_content, content_metadata, training_config
            )
            
            # Export to dictionary format
            training_content = self.training_agent.export_assessment_to_dict(assessment)
            
            logger.info(f"Generated training content with {assessment.total_questions} questions")
            
            return {
                "status": "success",
                "message": f"Generated {assessment.total_questions} training questions",
                "training_content": training_content,
                "metadata": {
                    "kb_id": kb_id,
                    "generated_at": datetime.now().isoformat(),
                    "question_count": assessment.total_questions,
                    "estimated_time": assessment.estimated_time,
                    "topics_covered": assessment.topics_covered
                }
            }
            
        except Exception as e:
            logger.error(f"Training content generation failed for KB {kb_id}: {e}")
            return {
                "status": "error",
                "message": f"Training generation failed: {str(e)}",
                "training_content": None
            }
    
    def _extract_content_from_kb_data(self, content_data: Dict[str, Any]) -> str:
        """Extract and combine content from different agent results."""
        combined_content = []
        
        # Extract from different agent types
        for agent_type, agent_results in content_data.items():
            if not isinstance(agent_results, list):
                continue
            
            for result in agent_results:
                if result.get("status") != "completed":
                    continue
                
                content = result.get("content", {})
                
                # Extract text content based on agent type
                if agent_type == "text":
                    text = content.get("full_text", content.get("text", ""))
                    if text:
                        combined_content.append(f"=== Text Content ===\n{text}\n")
                
                elif agent_type == "pdf":
                    text = content.get("full_text", content.get("text", ""))
                    if text:
                        combined_content.append(f"=== PDF Content ===\n{text}\n")
                
                elif agent_type == "audio":
                    transcription = content.get("full_transcription", content.get("transcription", ""))
                    if transcription:
                        combined_content.append(f"=== Audio Transcription ===\n{transcription}\n")
                
                elif agent_type == "video":
                    # Extract OCR text and audio transcription from video
                    frames_text = []
                    if "frames_base64" in content:
                        # This would need OCR results - for now skip
                        pass
                    
                    # Add any analysis text
                    analysis = result.get("analysis", {})
                    if isinstance(analysis, dict) and "ai_analysis" in analysis:
                        combined_content.append(f"=== Video Analysis ===\n{analysis['ai_analysis']}\n")
                
                elif agent_type == "image":
                    # **PRIORITY 1**: Extract structured educational content first
                    educational_content = content.get("educational_content", {})
                    if educational_content and educational_content.get("full_text_content"):
                        # Use the comprehensive extracted content
                        image_content_parts = [f"=== Image Educational Content ==="]

                        # Add full text content
                        full_text = educational_content.get("full_text_content", "")
                        if full_text:
                            image_content_parts.append(f"\n{full_text}\n")

                        # Add structured content
                        key_concepts = educational_content.get("key_concepts", [])
                        if key_concepts:
                            image_content_parts.append(f"\nKey Concepts: {', '.join(key_concepts)}")

                        commands = educational_content.get("commands", [])
                        if commands:
                            image_content_parts.append("\n\nCommands/Functions:")
                            for cmd in commands[:20]:  # Limit to 20 commands
                                name = cmd.get("name", "")
                                desc = cmd.get("description", "")
                                if name and desc:
                                    image_content_parts.append(f"  • {name}: {desc}")

                        topics = educational_content.get("topics", [])
                        if topics:
                            image_content_parts.append("\n\nTopics:")
                            for topic in topics:
                                topic_name = topic.get("topic", "")
                                topic_desc = topic.get("description", "")
                                if topic_name:
                                    image_content_parts.append(f"  • {topic_name}: {topic_desc}")

                        combined_content.append("\n".join(image_content_parts) + "\n")

                    # Fallback to extracted_text from OCR
                    elif content.get("extracted_text"):
                        combined_content.append(f"=== Image OCR Text ===\n{content['extracted_text']}\n")

                    # Final fallback to ai_analysis
                    else:
                        analysis = result.get("analysis", {})
                        if isinstance(analysis, dict) and "ai_analysis" in analysis:
                            combined_content.append(f"=== Image Analysis ===\n{analysis['ai_analysis']}\n")
                
                # Also extract AI analysis from any agent
                analysis = result.get("analysis", {})
                if isinstance(analysis, dict) and "ai_analysis" in analysis:
                    ai_text = analysis["ai_analysis"]
                    if ai_text and ai_text not in "\n".join(combined_content):
                        combined_content.append(f"=== {agent_type.upper()} Analysis ===\n{ai_text}\n")
        
        return "\n".join(combined_content)
    
    async def generate_mcq_from_content(self, content: str, content_metadata: Dict[str, Any],
                                      mcq_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate MCQ questions specifically from content."""
        try:
            # Configure for MCQ-only generation
            config = mcq_config or {}
            config.update({
                "question_types": ["mcq"],
                "question_count": config.get("question_count", 10)
            })
            
            assessment = await self.training_agent.generate_assessment(
                content, content_metadata, config
            )
            
            # Extract only MCQ questions
            mcq_questions = [q for q in assessment.questions if q.question_type == "mcq"]
            
            return {
                "status": "success",
                "mcq_count": len(mcq_questions),
                "questions": [
                    {
                        "id": i + 1,
                        "type": "mcq",
                        "question": q.question_text,
                        "options": q.options,
                        "correct_answer": q.correct_answer,
                        "explanation": q.explanation,
                        "difficulty": q.difficulty_level,
                        "topic": q.topic
                    }
                    for i, q in enumerate(mcq_questions)
                ]
            }
            
        except Exception as e:
            logger.error(f"MCQ generation failed: {e}")
            return {
                "status": "error",
                "message": f"MCQ generation failed: {str(e)}",
                "questions": []
            }
    
    async def generate_mixed_assessment(self, content: str, content_metadata: Dict[str, Any],
                                      assessment_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mixed assessment with different question types."""
        try:
            config = assessment_config or {
                "question_types": ["mcq", "open_ended", "fill_blank"],
                "question_count": 15
            }
            
            assessment = await self.training_agent.generate_assessment(
                content, content_metadata, config
            )
            
            return {
                "status": "success",
                "assessment": self.training_agent.export_assessment_to_dict(assessment)
            }
            
        except Exception as e:
            logger.error(f"Mixed assessment generation failed: {e}")
            return {
                "status": "error",
                "message": f"Assessment generation failed: {str(e)}",
                "assessment": None
            }
    
    async def get_learning_content_from_kb(self, kb_id: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract learning content summary from knowledge base for pre-study phase."""
        try:
            logger.info(f"Extracting learning content for KB: {kb_id}")

            # Extract content from different agent results
            combined_content = self._extract_content_from_kb_data(content_data)

            if not combined_content.strip():
                return {
                    "status": "error",
                    "message": "No content available for learning content generation"
                }

            # Use training agent to analyze and extract learning content
            # Smart content management: use chunking for long content to preserve quality
            content_length = len(combined_content)
            logger.info(f"Content length: {content_length:,} characters")

            if content_length > 20000:  # Use chunking for anything > 20K chars
                logger.info(f"Content is long ({content_length:,} chars), using intelligent chunking to preserve quality...")
                learning_content = await self.training_agent.extract_learning_content_chunked(combined_content)
            else:
                logger.info(f"Content is manageable ({content_length:,} chars), using direct extraction...")
                learning_content = await self.training_agent.extract_learning_content(combined_content)

            logger.info(f"Extracted learning content with {len(learning_content.get('key_concepts', []))} key concepts")

            return {
                "status": "completed",
                "content": learning_content
            }

        except Exception as e:
            logger.error(f"Learning content extraction failed for KB {kb_id}: {e}")
            return {
                "status": "error",
                "message": f"Learning content extraction failed: {str(e)}"
            }

    def get_supported_question_types(self) -> List[str]:
        """Get list of supported question types."""
        return self.training_agent.supported_question_types

    def get_default_config(self) -> Dict[str, Any]:
        """Get default training configuration."""
        return {
            "question_count": 10,
            "question_types": ["mcq", "open_ended"],
            "difficulty_levels": ["beginner", "intermediate", "advanced"],
            "include_explanations": True,
            "time_limit": 600
        }


# Global instance
training_service = TrainingService()