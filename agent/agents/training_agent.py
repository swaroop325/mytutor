"""
Training Agent - Specialized agent for generating educational assessments and training content
Handles: MCQ generation, question creation, assessment design, learning objectives
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
from datetime import datetime
from dataclasses import dataclass
import boto3

# Import model configuration system
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.model_manager import model_config_manager

logger = logging.getLogger(__name__)


@dataclass
class AssessmentQuestion:
    """Represents a single assessment question with metadata."""
    question_type: str  # "mcq", "open_ended", "fill_blank", "match", "true_false"
    question_text: str
    options: Optional[List[str]] = None  # For MCQ
    correct_answer: Union[str, List[str], Dict[str, str]] = ""  # String, list, or dict for matching
    explanation: str = ""
    difficulty_level: str = "intermediate"  # "beginner", "intermediate", "advanced"
    learning_objective: str = ""
    cognitive_level: str = "comprehension"  # Bloom's taxonomy level
    confidence_score: float = 0.8
    topic: str = ""
    estimated_time: int = 60  # seconds
    
    # Additional fields for specific question types
    left_column: Optional[List[str]] = None  # For matching questions
    right_column: Optional[List[str]] = None  # For matching questions
    correct_matches: Optional[Dict[str, str]] = None  # For matching questions
    sample_answer: Optional[str] = None  # For open-ended and scenario questions
    assessment_rubric: Optional[str] = None  # For open-ended questions
    context_clues: Optional[str] = None  # For fill-in-blank questions
    misconception_addressed: Optional[str] = None  # For true/false questions
    scenario_context: Optional[str] = None  # For scenario questions
    key_considerations: Optional[List[str]] = None  # For scenario questions
    assessment_criteria: Optional[str] = None  # For scenario questions


@dataclass
class AssessmentSet:
    """Complete assessment set with multiple questions."""
    content_source: str
    questions: List[AssessmentQuestion]
    total_questions: int
    difficulty_distribution: Dict[str, int]
    cognitive_level_distribution: Dict[str, int]
    estimated_time: int
    learning_objectives: List[str]
    topics_covered: List[str]
    assessment_metadata: Dict[str, Any]


class TrainingAgent:
    """Specialized agent for generating educational assessments and training content."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        
        # Model configuration - use Sonnet for complex reasoning tasks
        self.model_config = model_config_manager.get_model_for_agent("training") or \
                           model_config_manager.get_model_for_agent("text")
        
        # Assessment generation parameters
        self.default_question_count = 10
        self.max_questions_per_request = 15
        self.supported_question_types = [
            "mcq", "open_ended", "fill_blank", "match", "true_false", "scenario"
        ]
        
        logger.info("Training Agent initialized")
    
    def can_process(self, content_type: str) -> bool:
        """Check if this agent can generate training content for the given content type."""
        # Training agent can work with any processed content
        return True
    
    async def generate_assessment(self, content: str, content_metadata: Dict[str, Any], 
                                assessment_config: Optional[Dict[str, Any]] = None) -> AssessmentSet:
        """Generate a complete assessment set from content."""
        try:
            print(f"🎓 TRAINING Agent generating assessment from content")
            logger.info("Starting assessment generation")
            
            # Parse assessment configuration
            config = self._parse_assessment_config(assessment_config or {})
            
            # Analyze content for assessment generation
            content_analysis = await self._analyze_content_for_assessment(content, content_metadata)
            
            # Generate questions based on content and configuration
            questions = await self._generate_questions(content, content_analysis, config)
            
            # Apply quality management
            questions = self._apply_quality_management(questions, content_analysis, config)
            
            # Create assessment set
            assessment_set = self._create_assessment_set(
                content_metadata.get('filename', 'Unknown'),
                questions,
                content_analysis,
                config
            )
            
            print(f"✅ TRAINING Agent generated {len(questions)} questions")
            logger.info(f"Assessment generation completed: {len(questions)} questions")
            
            return assessment_set
            
        except Exception as e:
            logger.error(f"Assessment generation failed: {e}", exc_info=True)
            print(f"❌ TRAINING Agent error: {e}")
            # Return empty assessment set on error
            return AssessmentSet(
                content_source=content_metadata.get('filename', 'Unknown'),
                questions=[],
                total_questions=0,
                difficulty_distribution={},
                cognitive_level_distribution={},
                estimated_time=0,
                learning_objectives=[],
                topics_covered=[],
                assessment_metadata={"error": str(e)}
            )

    async def extract_learning_content(self, content: str) -> Dict[str, Any]:
        """Extract learning content summary for pre-study phase."""
        try:
            print(f"📚 Extracting learning content from {len(content):,} characters")

            # Smart content handling: extract key sections instead of simple truncation
            if len(content) > 20000:
                print(f"⚠️ Warning: Content is long ({len(content):,} chars). Consider using extract_learning_content_chunked() for better results.")
                content_excerpt = self._extract_key_content_for_questions(content, max_length=18000)
            else:
                content_excerpt = content

            prompt = f"""Analyze this educational content and extract key learning information for students to study before taking an assessment.

Content:
{content_excerpt}

Provide a comprehensive analysis in JSON format with:
1. summary: A 2-3 paragraph overview of what this content covers (be specific to the actual content, not generic)
2. key_concepts: Array of 5-10 specific key concepts/terms students should understand
3. learning_objectives: Array of 4-7 specific learning objectives (what students will be able to do after studying)
4. topics_covered: Array of 6-12 specific topics covered in the content
5. estimated_study_time: Estimated study time in minutes based on content depth and complexity

Format response as valid JSON:
{{
    "summary": "specific detailed summary of this content...",
    "key_concepts": ["specific concept 1", "specific concept 2", ...],
    "learning_objectives": ["specific objective 1", ...],
    "topics_covered": ["specific topic 1", "specific topic 2", ...],
    "estimated_study_time": 15
}}

Be specific to the actual content - do not use generic placeholders."""

            model_spec = self.model_config
            response = self.bedrock_client.invoke_model(
                modelId=model_spec.model_id if model_spec else "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )

            result = json.loads(response['body'].read())
            response_text = result['content'][0]['text']

            # Parse JSON response
            try:
                learning_content = json.loads(response_text)

                # Validate required fields
                required_fields = ["summary", "key_concepts", "learning_objectives", "topics_covered", "estimated_study_time"]
                for field in required_fields:
                    if field not in learning_content:
                        raise ValueError(f"Missing required field: {field}")

                print(f"✅ Extracted learning content with {len(learning_content['key_concepts'])} concepts")
                return learning_content

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse AI response, using fallback: {e}")
                # Return structured fallback
                return self._create_fallback_learning_content(content)

        except Exception as e:
            logger.error(f"Learning content extraction failed: {e}")
            return self._create_fallback_learning_content(content)

    def _create_fallback_learning_content(self, content: str) -> Dict[str, Any]:
        """Create fallback learning content when AI extraction fails."""
        # Extract some basic info from content
        word_count = len(content.split())
        estimated_time = max(5, min(30, word_count // 200))  # 200 words per minute reading

        return {
            "summary": "This course material covers important concepts and information. "
                      "Review the content carefully to understand the key principles and their applications. "
                      "Focus on understanding the relationships between different concepts.",
            "key_concepts": [
                "Core principles and definitions",
                "Key methodologies and approaches",
                "Practical applications",
                "Important relationships and connections",
                "Critical thinking and analysis"
            ],
            "learning_objectives": [
                "Understand the fundamental concepts presented",
                "Apply learned principles to new situations",
                "Analyze relationships between different topics",
                "Evaluate different approaches and methods"
            ],
            "topics_covered": [
                "Introduction and foundational concepts",
                "Core principles and theories",
                "Practical applications and examples",
                "Advanced topics and extensions"
            ],
            "estimated_study_time": estimated_time
        }

    async def extract_learning_content_chunked(self, content: str) -> Dict[str, Any]:
        """Extract learning content from long content using intelligent chunking."""
        try:
            print(f"📚 Processing long content ({len(content)} chars) with intelligent chunking...")
            
            # Split content into meaningful chunks (by paragraphs, sections, etc.)
            chunks = self._intelligent_content_chunking(content, max_chunk_size=15000)
            print(f"📄 Split content into {len(chunks)} chunks")
            
            # Extract learning content from each chunk
            chunk_results = []
            for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 chunks to avoid excessive API calls
                print(f"🔍 Processing chunk {i+1}/{min(len(chunks), 5)}...")
                chunk_result = await self.extract_learning_content(chunk)
                chunk_results.append(chunk_result)
            
            # Merge results intelligently
            merged_result = self._merge_learning_content_results(chunk_results)
            print(f"✅ Merged learning content from {len(chunk_results)} chunks")
            
            return merged_result
            
        except Exception as e:
            logger.error(f"Chunked learning content extraction failed: {e}")
            # Fallback to truncated version
            return await self.extract_learning_content(content[:15000])

    def _intelligent_content_chunking(self, content: str, max_chunk_size: int = 15000) -> List[str]:
        """Split content into meaningful chunks preserving context."""
        if len(content) <= max_chunk_size:
            return [content]
        
        chunks = []
        
        # Try to split by double newlines (paragraphs/sections)
        sections = content.split('\n\n')
        
        current_chunk = ""
        for section in sections:
            # If adding this section would exceed limit, save current chunk
            if len(current_chunk) + len(section) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = section
            else:
                current_chunk += "\n\n" + section if current_chunk else section
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If chunks are still too large, split by sentences
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_chunk_size:
                final_chunks.append(chunk)
            else:
                # Split by sentences
                sentences = chunk.split('. ')
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                        final_chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += ". " + sentence if current_chunk else sentence
                
                if current_chunk:
                    final_chunks.append(current_chunk.strip())
        
        return final_chunks

    def _merge_learning_content_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple learning content results into a comprehensive one."""
        if not results:
            return self._create_fallback_learning_content("")
        
        if len(results) == 1:
            return results[0]
        
        # Merge summaries
        summaries = [r.get('summary', '') for r in results if r.get('summary')]
        merged_summary = " ".join(summaries[:3])  # Use first 3 summaries
        
        # Merge and deduplicate concepts, objectives, topics
        all_concepts = []
        all_objectives = []
        all_topics = []
        
        for result in results:
            all_concepts.extend(result.get('key_concepts', []))
            all_objectives.extend(result.get('learning_objectives', []))
            all_topics.extend(result.get('topics_covered', []))
        
        # Deduplicate while preserving order
        unique_concepts = list(dict.fromkeys(all_concepts))[:12]  # Limit to 12
        unique_objectives = list(dict.fromkeys(all_objectives))[:10]  # Limit to 10
        unique_topics = list(dict.fromkeys(all_topics))[:15]  # Limit to 15
        
        # Calculate total estimated study time
        total_time = sum(r.get('estimated_study_time', 0) for r in results)
        
        return {
            "summary": merged_summary,
            "key_concepts": unique_concepts,
            "learning_objectives": unique_objectives,
            "topics_covered": unique_topics,
            "estimated_study_time": min(total_time, 60)  # Cap at 60 minutes
        }

    def _extract_key_content_for_questions(self, content: str, max_length: int = 3000) -> str:
        """Extract key content sections for question generation instead of simple truncation."""
        if len(content) <= max_length:
            return content
        
        # Try to extract key sections intelligently
        lines = content.split('\n')
        
        # Prioritize lines that look like headings, definitions, or key points
        key_lines = []
        regular_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line looks important (headings, definitions, bullet points, etc.)
            if (line.isupper() or  # ALL CAPS headings
                line.startswith('#') or  # Markdown headings
                line.startswith('*') or line.startswith('-') or  # Bullet points
                ':' in line or  # Definitions or key-value pairs
                line.endswith(':') or  # Section headers
                any(keyword in line.lower() for keyword in ['definition', 'important', 'key', 'note', 'remember'])):
                key_lines.append(line)
            else:
                regular_lines.append(line)
        
        # Build content starting with key lines
        result_lines = key_lines[:]
        current_length = sum(len(line) for line in result_lines)
        
        # Add regular lines until we reach the limit
        for line in regular_lines:
            if current_length + len(line) > max_length:
                break
            result_lines.append(line)
            current_length += len(line)
        
        return '\n'.join(result_lines)

    def _parse_assessment_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate assessment configuration."""
        return {
            "question_count": config.get("question_count", self.default_question_count),
            "question_types": config.get("question_types", ["mcq", "open_ended"]),
            "difficulty_levels": config.get("difficulty_levels", ["beginner", "intermediate", "advanced"]),
            "cognitive_levels": config.get("cognitive_levels", ["knowledge", "comprehension", "application", "analysis"]),
            "include_explanations": config.get("include_explanations", True),
            "time_limit": config.get("time_limit", 600),  # 10 minutes default
            "focus_topics": config.get("focus_topics", []),
            "learning_objectives": config.get("learning_objectives", []),
            "bloom_distribution": config.get("bloom_distribution", {
                "knowledge": 0.2,
                "comprehension": 0.3,
                "application": 0.3,
                "analysis": 0.15,
                "synthesis": 0.05,
                "evaluation": 0.0
            }),
            "difficulty_distribution": config.get("difficulty_distribution", {
                "beginner": 0.3,
                "intermediate": 0.5,
                "advanced": 0.2
            })
        }
    
    async def _analyze_content_for_assessment(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content to identify key concepts, topics, and learning opportunities."""
        try:
            prompt = f"""
Analyze this educational content for assessment generation:

Content Type: {metadata.get('content_type', 'Unknown')}
Source: {metadata.get('filename', 'Unknown')}

Content (first 3000 characters):
{content[:3000]}

Please analyze and provide:
1. Key learning concepts and topics
2. Important facts and definitions
3. Processes and procedures described
4. Relationships and connections between concepts
5. Difficulty level assessment
6. Suggested learning objectives
7. Areas suitable for different question types (MCQ, open-ended, etc.)
8. Bloom's taxonomy levels represented in the content

Respond in JSON format:
{{
    "key_concepts": ["concept1", "concept2"],
    "important_facts": ["fact1", "fact2"],
    "processes": ["process1", "process2"],
    "relationships": ["relationship1", "relationship2"],
    "difficulty_level": "intermediate",
    "learning_objectives": ["objective1", "objective2"],
    "question_opportunities": {{
        "mcq": ["topic1", "topic2"],
        "open_ended": ["topic3", "topic4"],
        "fill_blank": ["definition1", "definition2"]
    }},
    "bloom_levels": ["knowledge", "comprehension", "application"],
    "estimated_study_time": 30
}}
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_config.model_id if self.model_config else "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']
            
            # Parse JSON response
            try:
                analysis = json.loads(analysis_text)
                return analysis
            except json.JSONDecodeError:
                logger.warning("Failed to parse content analysis JSON, using fallback")
                return self._create_fallback_analysis(content, metadata)
                
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return self._create_fallback_analysis(content, metadata)
    
    def _create_fallback_analysis(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic content analysis when AI analysis fails."""
        words = content.split()
        return {
            "key_concepts": ["General concepts"],
            "important_facts": ["Key information"],
            "processes": [],
            "relationships": [],
            "difficulty_level": "intermediate",
            "learning_objectives": ["Understand the main content"],
            "question_opportunities": {
                "mcq": ["General knowledge"],
                "open_ended": ["Content comprehension"]
            },
            "bloom_levels": ["knowledge", "comprehension"],
            "estimated_study_time": max(10, len(words) // 200)  # Rough estimate
        }
    
    async def _generate_questions(self, content: str, analysis: Dict[str, Any], 
                                config: Dict[str, Any]) -> List[AssessmentQuestion]:
        """Generate assessment questions based on content analysis and configuration."""
        questions = []
        question_count = config["question_count"]
        question_types = config["question_types"]
        
        # Distribute questions across different types
        questions_per_type = max(1, question_count // len(question_types))
        
        for question_type in question_types:
            type_questions = await self._generate_questions_by_type(
                content, analysis, question_type, questions_per_type, config
            )
            questions.extend(type_questions)
            
            # Stop if we have enough questions
            if len(questions) >= question_count:
                break
        
        # Trim to exact count if we generated too many
        return questions[:question_count]
    
    async def _generate_questions_by_type(self, content: str, analysis: Dict[str, Any],
                                        question_type: str, count: int, 
                                        config: Dict[str, Any]) -> List[AssessmentQuestion]:
        """Generate questions of a specific type."""
        try:
            # Get relevant topics for this question type
            relevant_topics = analysis.get("question_opportunities", {}).get(question_type, [])
            key_concepts = analysis.get("key_concepts", [])
            
            prompt = self._create_question_generation_prompt(
                content, analysis, question_type, count, relevant_topics, key_concepts
            )
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_config.model_id if self.model_config else "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 3000,
                    "temperature": 0.2,  # Slightly higher for creative question generation
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            questions_text = result['content'][0]['text']
            
            # Parse questions from response
            questions = self._parse_generated_questions(questions_text, question_type, analysis)
            
            print(f"✅ Generated {len(questions)} {question_type} questions")
            return questions
            
        except Exception as e:
            logger.error(f"Question generation failed for type {question_type}: {e}")
            return []
    
    def _create_question_generation_prompt(self, content: str, analysis: Dict[str, Any],
                                         question_type: str, count: int, 
                                         topics: List[str], concepts: List[str]) -> str:
        """Create a prompt for generating specific types of questions."""
        
        # Smart content handling: use key excerpts instead of truncation
        base_content = self._extract_key_content_for_questions(content, 3000)  # More generous limit with smart extraction
        
        if question_type == "mcq":
            return f"""
Generate {count} high-quality multiple-choice questions based on this content:

Content: {base_content}

Key Concepts: {', '.join(concepts)}
Focus Topics: {', '.join(topics)}

Requirements for MCQ Generation:
- Create questions that test understanding, application, and analysis - not just memorization
- Provide 4 options (A, B, C, D) with only one correct answer
- Design intelligent distractors that:
  * Test common misconceptions about the topic
  * Include partially correct information that might confuse students
  * Use similar terminology but incorrect context
  * Represent logical but incorrect reasoning paths
- Vary difficulty levels (beginner, intermediate, advanced)
- Include clear explanations for correct answers AND why distractors are incorrect
- Focus on key concepts, cause-and-effect relationships, and practical applications
- Avoid trivial details or trick questions

Distractor Design Guidelines:
- Make distractors plausible and related to the content
- Include common student errors or misconceptions
- Use terminology from the content but in incorrect contexts
- Create options that test different levels of understanding

Format each question as JSON:
{{
    "question": "Question text here?",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "correct_answer": "A",
    "explanation": "Explanation of why A is correct and why B, C, D are incorrect",
    "difficulty": "intermediate",
    "topic": "relevant topic",
    "cognitive_level": "application",
    "distractor_rationale": "Brief explanation of how distractors were designed"
}}

Generate {count} questions in a JSON array.
"""
        
        elif question_type == "open_ended":
            return f"""
Generate {count} open-ended questions that encourage critical thinking and deep understanding based on this content:

Content: {base_content}

Key Concepts: {', '.join(concepts)}

Requirements for Open-Ended Questions:
- Focus on higher-order thinking skills: analysis, synthesis, evaluation, and creation
- Encourage students to explain reasoning, make connections, and justify conclusions
- Avoid simple recall or yes/no questions
- Promote critical thinking through:
  * Comparison and contrast of concepts
  * Cause-and-effect analysis
  * Problem-solving scenarios
  * Application to real-world situations
  * Evaluation of different perspectives or approaches
- Vary cognitive complexity across Bloom's taxonomy levels
- Include detailed rubric guidelines for assessment

Question Types to Generate:
- Analysis questions: "Analyze the relationship between..."
- Synthesis questions: "How would you combine these concepts to..."
- Evaluation questions: "Evaluate the effectiveness of..."
- Application questions: "How would you apply this concept to..."
- Comparison questions: "Compare and contrast..."

Format each question as JSON:
{{
    "question": "Question text here?",
    "sample_answer": "Detailed example of a comprehensive answer with key points",
    "assessment_rubric": "Brief rubric for evaluating answers (excellent, good, fair, poor criteria)",
    "difficulty": "intermediate",
    "topic": "relevant topic",
    "cognitive_level": "analysis",
    "estimated_time": 180,
    "key_concepts_tested": ["concept1", "concept2"]
}}

Generate {count} questions in a JSON array.
"""
        
        elif question_type == "fill_blank":
            return f"""
Generate {count} fill-in-the-blank questions based on key definitions and concepts:

Content: {base_content}

Key Concepts: {', '.join(concepts)}

Requirements for Fill-in-the-Blank Questions:
- Focus on important terms, definitions, processes, and key factual information
- Create blanks that test essential knowledge and understanding
- Provide sufficient context clues without making answers obvious
- Vary difficulty by adjusting context complexity and specificity
- Include multiple blanks per question when appropriate for complex concepts
- Test both terminology and conceptual understanding

Question Design Guidelines:
- Use clear, complete sentences with strategic blank placement
- Ensure context provides enough information for educated guessing
- Avoid ambiguous blanks that could have multiple correct answers
- Include numerical values, dates, names, and technical terms
- Test cause-and-effect relationships and process steps

Format each question as JSON:
{{
    "question": "The process of _____ converts light energy into chemical energy through the use of _____ and carbon dioxide.",
    "correct_answer": ["photosynthesis", "water"] or "photosynthesis, water",
    "explanation": "Detailed explanation of the concept and why these answers are correct",
    "difficulty": "intermediate",
    "topic": "relevant topic",
    "cognitive_level": "knowledge",
    "context_clues": "Brief note about what context clues help answer this question"
}}

Generate {count} questions in a JSON array.
"""
        
        elif question_type == "match":
            return f"""
Generate {count} matching questions based on relationships and categories in the content:

Content: {base_content}

Key Concepts: {', '.join(concepts)}

Requirements for Matching Questions:
- Create logical pairs that test understanding of relationships
- Include categories like: terms-definitions, causes-effects, problems-solutions, concepts-examples
- Provide 4-6 items in each column for optimal difficulty
- Ensure all matches are clearly related and unambiguous
- Include distractors that are plausible but incorrect
- Test conceptual relationships rather than simple memorization

Matching Categories to Consider:
- Terms and their definitions
- Concepts and their applications
- Causes and their effects
- Problems and their solutions
- Categories and their examples
- Processes and their outcomes

Format each question as JSON:
{{
    "question": "Match each concept with its correct definition:",
    "left_column": ["Term 1", "Term 2", "Term 3", "Term 4"],
    "right_column": ["Definition A", "Definition B", "Definition C", "Definition D"],
    "correct_matches": {{"Term 1": "Definition A", "Term 2": "Definition B", "Term 3": "Definition C", "Term 4": "Definition D"}},
    "explanation": "Explanation of each correct match and why they are paired",
    "difficulty": "intermediate",
    "topic": "relevant topic",
    "cognitive_level": "comprehension"
}}

Generate {count} questions in a JSON array.
"""
        
        elif question_type == "true_false":
            return f"""
Generate {count} true/false questions with detailed explanations:

Content: {base_content}

Key Concepts: {', '.join(concepts)}

Requirements for True/False Questions:
- Test important concepts, principles, and common misconceptions
- Create statements that require understanding, not just memorization
- Avoid trivial details, trick questions, or ambiguous statements
- Balance true and false questions (roughly 50/50 split)
- Focus on key concepts, cause-and-effect relationships, and principles
- Include statements that test common student misconceptions

Statement Design Guidelines:
- Make statements clear and unambiguous
- Test understanding of core concepts and principles
- Include statements about processes, relationships, and applications
- Avoid absolute terms unless they are genuinely always true/false
- Create statements that require analysis of the concept

Format each question as JSON:
{{
    "question": "Clear, unambiguous statement to evaluate for truth",
    "correct_answer": "true",
    "explanation": "Detailed explanation of why this statement is true/false, including relevant context and clarification of any misconceptions",
    "difficulty": "intermediate",
    "topic": "relevant topic",
    "cognitive_level": "comprehension",
    "misconception_addressed": "Brief note about what common misconception this tests, if applicable"
}}

Generate {count} questions in a JSON array.
"""
        
        elif question_type == "scenario":
            return f"""
Generate {count} scenario-based questions for application testing based on this content:

Content: {base_content}

Key Concepts: {', '.join(concepts)}

Requirements for Scenario-Based Questions:
- Create realistic, practical scenarios that require application of the learned concepts
- Present complex situations that require analysis and problem-solving
- Include sufficient context and background information
- Test ability to apply knowledge to new situations
- Encourage critical thinking and decision-making
- Include multiple valid approaches or considerations

Scenario Design Guidelines:
- Set up realistic contexts relevant to the subject matter
- Present problems that require synthesis of multiple concepts
- Include enough detail for informed decision-making
- Ask for analysis, recommendations, or solutions
- Test practical application rather than theoretical knowledge
- Consider real-world constraints and considerations

Format each question as JSON:
{{
    "question": "Detailed scenario description followed by the question asking for analysis, solution, or recommendation",
    "scenario_context": "Additional background information about the scenario",
    "sample_answer": "Comprehensive example answer showing good analysis and reasoning",
    "key_considerations": ["Important factor 1", "Important factor 2", "Important factor 3"],
    "assessment_criteria": "What makes a good answer to this scenario",
    "difficulty": "advanced",
    "topic": "relevant topic",
    "cognitive_level": "application",
    "estimated_time": 300
}}

Generate {count} questions in a JSON array.
"""
        
        else:
            # Default format for other question types
            return f"""
Generate {count} {question_type} questions based on this content:

Content: {base_content}

Key Concepts: {', '.join(concepts)}

Create educational questions that test understanding of the key concepts.
Format as JSON array with question, answer, explanation, difficulty, and topic fields.
"""
    
    def _parse_generated_questions(self, questions_text: str, question_type: str, 
                                 analysis: Dict[str, Any]) -> List[AssessmentQuestion]:
        """Parse generated questions from AI response."""
        try:
            # Try to extract JSON from the response
            questions_data = json.loads(questions_text)
            
            if not isinstance(questions_data, list):
                questions_data = [questions_data]
            
            questions = []
            for q_data in questions_data:
                try:
                    # Base question data
                    question = AssessmentQuestion(
                        question_type=question_type,
                        question_text=q_data.get("question", ""),
                        options=q_data.get("options", None),
                        correct_answer=q_data.get("correct_answer", ""),
                        explanation=q_data.get("explanation", ""),
                        difficulty_level=q_data.get("difficulty", "intermediate"),
                        learning_objective=q_data.get("learning_objective", ""),
                        cognitive_level=q_data.get("cognitive_level", "comprehension"),
                        confidence_score=0.8,
                        topic=q_data.get("topic", ""),
                        estimated_time=q_data.get("estimated_time", 60)
                    )
                    
                    # Add question-type specific fields
                    if question_type == "match":
                        question.left_column = q_data.get("left_column", [])
                        question.right_column = q_data.get("right_column", [])
                        question.correct_matches = q_data.get("correct_matches", {})
                    elif question_type == "open_ended":
                        question.sample_answer = q_data.get("sample_answer", "")
                        question.assessment_rubric = q_data.get("assessment_rubric", "")
                    elif question_type == "fill_blank":
                        question.context_clues = q_data.get("context_clues", "")
                    elif question_type == "true_false":
                        question.misconception_addressed = q_data.get("misconception_addressed", "")
                    elif question_type == "scenario":
                        question.scenario_context = q_data.get("scenario_context", "")
                        question.key_considerations = q_data.get("key_considerations", [])
                        question.assessment_criteria = q_data.get("assessment_criteria", "")
                        question.sample_answer = q_data.get("sample_answer", "")
                    
                    if question.question_text:  # Only add if we have a question
                        questions.append(question)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse individual question: {e}")
                    continue
            
            return questions
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse questions JSON, attempting text parsing")
            return self._parse_questions_from_text(questions_text, question_type)
    
    def _parse_questions_from_text(self, text: str, question_type: str) -> List[AssessmentQuestion]:
        """Fallback method to parse questions from plain text."""
        questions = []
        # Basic text parsing - this is a simplified fallback
        lines = text.split('\n')
        current_question = None
        
        for line in lines:
            line = line.strip()
            if line and ('?' in line or line.endswith(':')):
                if current_question:
                    questions.append(current_question)
                
                current_question = AssessmentQuestion(
                    question_type=question_type,
                    question_text=line,
                    difficulty_level="intermediate",
                    cognitive_level="comprehension"
                )
        
        if current_question:
            questions.append(current_question)
        
        return questions[:5]  # Limit fallback questions
    
    def _create_assessment_set(self, content_source: str, questions: List[AssessmentQuestion],
                             analysis: Dict[str, Any], config: Dict[str, Any]) -> AssessmentSet:
        """Create a complete assessment set from generated questions."""
        
        # Calculate distributions
        difficulty_dist = {}
        cognitive_dist = {}
        total_time = 0
        topics = set()
        
        for question in questions:
            # Difficulty distribution
            diff = question.difficulty_level
            difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1
            
            # Cognitive level distribution
            cog = question.cognitive_level
            cognitive_dist[cog] = cognitive_dist.get(cog, 0) + 1
            
            # Time and topics
            total_time += question.estimated_time
            if question.topic:
                topics.add(question.topic)
        
        # Use generated learning objectives if available
        learning_objectives = (analysis.get("generated_learning_objectives") or 
                             analysis.get("learning_objectives", []) or 
                             config.get("learning_objectives", []))
        
        assessment_set = AssessmentSet(
            content_source=content_source,
            questions=questions,
            total_questions=len(questions),
            difficulty_distribution=difficulty_dist,
            cognitive_level_distribution=cognitive_dist,
            estimated_time=total_time,
            learning_objectives=learning_objectives,
            topics_covered=list(topics),
            assessment_metadata={
                "generated_at": datetime.now().isoformat(),
                "content_analysis": analysis,
                "generation_config": config,
                "agent_version": "1.0"
            }
        )
        
        # Calculate and add quality score
        quality_score = self.calculate_assessment_quality_score(assessment_set)
        assessment_set.assessment_metadata["quality_score"] = quality_score
        
        return assessment_set
    
    def export_assessment_to_dict(self, assessment: AssessmentSet) -> Dict[str, Any]:
        """Export assessment set to dictionary format for storage/API."""
        return {
            "content_source": assessment.content_source,
            "total_questions": assessment.total_questions,
            "estimated_time": assessment.estimated_time,
            "difficulty_distribution": assessment.difficulty_distribution,
            "cognitive_level_distribution": assessment.cognitive_level_distribution,
            "learning_objectives": assessment.learning_objectives,
            "topics_covered": assessment.topics_covered,
            "questions": [
                self._export_question_to_dict(q, i + 1)
                for i, q in enumerate(assessment.questions)
            ],
            "metadata": assessment.assessment_metadata
        }
    
    def _export_question_to_dict(self, question: AssessmentQuestion, question_id: int) -> Dict[str, Any]:
        """Export a single question to dictionary format."""
        base_dict = {
            "id": question_id,
            "type": question.question_type,
            "question": question.question_text,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
            "difficulty": question.difficulty_level,
            "cognitive_level": question.cognitive_level,
            "topic": question.topic,
            "estimated_time": question.estimated_time,
            "confidence": question.confidence_score
        }
        
        # Add question-type specific fields
        if question.question_type == "mcq":
            base_dict["options"] = question.options
        elif question.question_type == "match":
            base_dict["left_column"] = question.left_column
            base_dict["right_column"] = question.right_column
            base_dict["correct_matches"] = question.correct_matches
        elif question.question_type == "open_ended":
            base_dict["sample_answer"] = question.sample_answer
            base_dict["assessment_rubric"] = question.assessment_rubric
        elif question.question_type == "fill_blank":
            base_dict["context_clues"] = question.context_clues
        elif question.question_type == "true_false":
            base_dict["misconception_addressed"] = question.misconception_addressed
        elif question.question_type == "scenario":
            base_dict["scenario_context"] = question.scenario_context
            base_dict["key_considerations"] = question.key_considerations
            base_dict["assessment_criteria"] = question.assessment_criteria
            base_dict["sample_answer"] = question.sample_answer
        
        return base_dict
    
    def assess_question_difficulty(self, question: AssessmentQuestion, content_analysis: Dict[str, Any]) -> str:
        """Assess and validate question difficulty based on content and cognitive level."""
        # Bloom's taxonomy complexity mapping
        cognitive_complexity = {
            "knowledge": 1,
            "comprehension": 2,
            "application": 3,
            "analysis": 4,
            "synthesis": 5,
            "evaluation": 6
        }
        
        # Base difficulty from cognitive level
        cognitive_score = cognitive_complexity.get(question.cognitive_level.lower(), 2)
        
        # Adjust based on question type complexity
        type_complexity = {
            "mcq": 1,
            "true_false": 1,
            "fill_blank": 2,
            "match": 2,
            "open_ended": 3,
            "scenario": 4
        }
        
        type_score = type_complexity.get(question.question_type, 2)
        
        # Calculate overall difficulty
        total_score = (cognitive_score + type_score) / 2
        
        if total_score <= 2:
            return "beginner"
        elif total_score <= 3.5:
            return "intermediate"
        else:
            return "advanced"
    
    def balance_cognitive_levels(self, questions: List[AssessmentQuestion], 
                               target_distribution: Dict[str, float]) -> List[AssessmentQuestion]:
        """Balance questions across Bloom's taxonomy levels according to target distribution."""
        if not questions:
            return questions
        
        # Count current distribution
        current_counts = {}
        for question in questions:
            level = question.cognitive_level.lower()
            current_counts[level] = current_counts.get(level, 0) + 1
        
        total_questions = len(questions)
        balanced_questions = []
        
        # Sort questions by cognitive level for balanced selection
        questions_by_level = {}
        for question in questions:
            level = question.cognitive_level.lower()
            if level not in questions_by_level:
                questions_by_level[level] = []
            questions_by_level[level].append(question)
        
        # Select questions according to target distribution
        for level, target_ratio in target_distribution.items():
            target_count = int(total_questions * target_ratio)
            available_questions = questions_by_level.get(level, [])
            
            # Take up to target_count questions from this level
            selected = available_questions[:target_count]
            balanced_questions.extend(selected)
        
        # Fill remaining slots with any available questions
        used_questions = set(id(q) for q in balanced_questions)
        remaining_questions = [q for q in questions if id(q) not in used_questions]
        
        while len(balanced_questions) < total_questions and remaining_questions:
            balanced_questions.append(remaining_questions.pop(0))
        
        return balanced_questions[:total_questions]
    
    def generate_learning_objectives(self, content_analysis: Dict[str, Any], 
                                   questions: List[AssessmentQuestion]) -> List[str]:
        """Generate learning objectives based on content analysis and questions."""
        objectives = []
        
        # Extract key concepts and topics
        key_concepts = content_analysis.get("key_concepts", [])
        topics_covered = set(q.topic for q in questions if q.topic)
        
        # Generate objectives based on Bloom's taxonomy levels present
        cognitive_levels = set(q.cognitive_level.lower() for q in questions)
        
        for concept in key_concepts[:5]:  # Limit to top 5 concepts
            for level in cognitive_levels:
                if level == "knowledge":
                    objectives.append(f"Identify and recall key information about {concept}")
                elif level == "comprehension":
                    objectives.append(f"Explain and interpret concepts related to {concept}")
                elif level == "application":
                    objectives.append(f"Apply knowledge of {concept} to solve problems")
                elif level == "analysis":
                    objectives.append(f"Analyze relationships and components of {concept}")
                elif level == "synthesis":
                    objectives.append(f"Create new solutions using {concept}")
                elif level == "evaluation":
                    objectives.append(f"Evaluate and critique approaches involving {concept}")
        
        # Remove duplicates and limit to reasonable number
        unique_objectives = list(set(objectives))
        return unique_objectives[:8]  # Limit to 8 objectives
    
    def calculate_assessment_quality_score(self, assessment: AssessmentSet) -> float:
        """Calculate overall quality score for the assessment."""
        if not assessment.questions:
            return 0.0
        
        quality_factors = []
        
        # 1. Question type diversity (0-1)
        unique_types = set(q.question_type for q in assessment.questions)
        type_diversity = min(len(unique_types) / 5, 1.0)  # Max 5 types
        quality_factors.append(type_diversity * 0.2)
        
        # 2. Cognitive level distribution (0-1)
        cognitive_levels = [q.cognitive_level.lower() for q in assessment.questions]
        unique_cognitive = set(cognitive_levels)
        cognitive_diversity = min(len(unique_cognitive) / 4, 1.0)  # Max 4 levels typically
        quality_factors.append(cognitive_diversity * 0.25)
        
        # 3. Difficulty balance (0-1)
        difficulties = [q.difficulty_level for q in assessment.questions]
        unique_difficulties = set(difficulties)
        difficulty_balance = min(len(unique_difficulties) / 3, 1.0)  # 3 difficulty levels
        quality_factors.append(difficulty_balance * 0.2)
        
        # 4. Average confidence score (0-1)
        avg_confidence = sum(q.confidence_score for q in assessment.questions) / len(assessment.questions)
        quality_factors.append(avg_confidence * 0.2)
        
        # 5. Explanation quality (0-1) - based on explanation length and presence
        explanations_present = sum(1 for q in assessment.questions if q.explanation and len(q.explanation) > 20)
        explanation_quality = explanations_present / len(assessment.questions)
        quality_factors.append(explanation_quality * 0.15)
        
        return sum(quality_factors)
    
    def _apply_quality_management(self, questions: List[AssessmentQuestion], 
                                content_analysis: Dict[str, Any], 
                                config: Dict[str, Any]) -> List[AssessmentQuestion]:
        """Apply quality management to improve question set."""
        if not questions:
            return questions
        
        # 1. Assess and correct difficulty levels
        for question in questions:
            assessed_difficulty = self.assess_question_difficulty(question, content_analysis)
            question.difficulty_level = assessed_difficulty
        
        # 2. Balance cognitive levels according to target distribution
        target_bloom_distribution = config.get("bloom_distribution", {})
        if target_bloom_distribution:
            questions = self.balance_cognitive_levels(questions, target_bloom_distribution)
        
        # 3. Ensure minimum quality standards
        quality_questions = []
        for question in questions:
            # Skip questions with very low confidence or missing explanations
            if question.confidence_score >= 0.6 and question.explanation:
                quality_questions.append(question)
        
        # 4. Generate learning objectives if not provided
        if not config.get("learning_objectives"):
            generated_objectives = self.generate_learning_objectives(content_analysis, quality_questions)
            # Store in content_analysis for use in assessment creation
            content_analysis["generated_learning_objectives"] = generated_objectives
        
        return quality_questions


# Global instance
training_agent = TrainingAgent()