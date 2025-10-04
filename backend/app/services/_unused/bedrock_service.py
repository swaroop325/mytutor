import json
import boto3
from datetime import datetime
from typing import List, Optional
from app.core.config import settings
from app.schemas.course import CourseContent


class BedrockService:
    def __init__(self):
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.AWS_REGION,
        )

    async def analyze_course_content(
        self,
        content: str,
        images: Optional[List[str]] = None
    ) -> CourseContent:
        """
        Analyze course content using Amazon Bedrock with Claude multimodal.
        """
        try:
            content_blocks = [
                {
                    "type": "text",
                    "text": f"""Analyze the following course content and extract structured information in JSON format:
{{
    "title": "Course Title",
    "sections": ["Section 1", "Section 2", ...],
    "topics": ["Topic 1", "Topic 2", ...],
    "summary": "Brief course summary"
}}

Course Content:
{content}"""
                }
            ]

            # Add images if provided (base64 encoded)
            if images:
                for image in images:
                    content_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image
                        }
                    })

            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": content_blocks
                    }
                ],
                "temperature": 0.5
            }

            response = self.client.invoke_model(
                modelId=settings.BEDROCK_MODEL_ID,
                body=json.dumps(payload)
            )

            response_body = json.loads(response['body'].read())
            analysis_text = response_body['content'][0]['text']

            # Try to parse JSON from response
            try:
                course_data = json.loads(analysis_text)
                return CourseContent(**course_data)
            except json.JSONDecodeError:
                # Fallback if response is not JSON
                return CourseContent(
                    title="Extracted Course",
                    sections=["Introduction", "Main Content"],
                    topics=["General Topics"],
                    summary=analysis_text
                )

        except Exception as e:
            print(f"Error analyzing course content: {e}")
            raise

    async def build_knowledge_base(
        self,
        course_contents: List[CourseContent]
    ) -> dict:
        """
        Build a knowledge base from course contents.
        This can be integrated with Amazon Bedrock Knowledge Bases.
        """
        # For now, return a structured knowledge base
        # In production, this would create an actual Bedrock KB
        kb_id = f"kb-{hash(str(course_contents))}"

        return {
            "id": kb_id,
            "courses": [content.dict() for content in course_contents],
            "total_courses": len(course_contents),
            "created_at": str(datetime.utcnow())
        }


bedrock_service = BedrockService()
