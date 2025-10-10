"""
Agent Manager - Coordinates all specialized agents
Routes files to appropriate agents and manages processing
"""
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

from .text_agent import text_agent
from .pdf_agent import pdf_agent
from .video_agent import video_agent
from .audio_agent import audio_agent
from .image_agent import image_agent


class AgentManager:
    """Manages and coordinates all specialized agents."""
    
    def __init__(self):
        self.agents = {
            "text": text_agent,
            "pdf": pdf_agent,
            "video": video_agent,
            "audio": audio_agent,
            "image": image_agent
        }
    
    def get_agent_for_file(self, file_path: str) -> Optional[str]:
        """Determine which agent should process a given file."""
        file_lower = file_path.lower()
        filename = os.path.basename(file_path).lower()
        
        # Check each agent's capabilities
        for agent_type, agent in self.agents.items():
            if agent.can_process(file_path):
                return agent_type
        
        # Fallback logic based on path structure
        if '/video/' in file_lower or '\\video\\' in file_lower:
            return "video"
        elif '/audio/' in file_lower or '\\audio\\' in file_lower:
            return "audio"
        elif '/image/' in file_lower or '\\image\\' in file_lower:
            return "image"
        elif '/document/' in file_lower or '\\document\\' in file_lower:
            if 'pdf' in filename:
                return "pdf"
            else:
                return "text"
        
        # Default fallback
        logger.warning(f"No specific agent found for {file_path}, defaulting to text agent")
        return "text"
    
    async def process_file(self, file_path: str, user_id: str, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Process a single file with the appropriate agent."""
        try:
            # Determine agent type if not specified
            if not agent_type:
                agent_type = self.get_agent_for_file(file_path)
            
            if agent_type not in self.agents:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # Get the appropriate agent
            agent = self.agents[agent_type]
            
            # Process the file
            logger.info(f"🤖 Routing {file_path} to {agent_type.upper()} agent")
            result = await agent.process_file(file_path, user_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Agent Manager error processing {file_path}: {e}")
            return {
                "agent_type": agent_type or "unknown",
                "file_path": file_path,
                "status": "error",
                "error": str(e)
            }
    
    async def process_files_batch(self, file_paths: List[str], user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Process multiple files with appropriate agents in parallel."""
        try:
            logger.info(f"Processing {len(file_paths)} files with specialized agents")
            
            # Group files by agent type
            agent_groups = {}
            for file_path in file_paths:
                agent_type = self.get_agent_for_file(file_path)
                if agent_type not in agent_groups:
                    agent_groups[agent_type] = []
                agent_groups[agent_type].append(file_path)
            
            logger.info(f"Agent distribution: {dict((k, len(v)) for k, v in agent_groups.items())}")
            
            # Process each group in parallel
            all_tasks = []
            for agent_type, files in agent_groups.items():
                for file_path in files:
                    task = self.process_file(file_path, user_id, agent_type)
                    all_tasks.append(task)
            
            # Wait for all processing to complete
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            # Group results by agent type
            agent_results = {}
            result_index = 0
            
            for agent_type, files in agent_groups.items():
                agent_results[agent_type] = []
                for _ in files:
                    result = results[result_index]
                    if isinstance(result, Exception):
                        agent_results[agent_type].append({
                            "agent_type": agent_type,
                            "status": "error",
                            "error": str(result)
                        })
                    else:
                        agent_results[agent_type].append(result)
                    result_index += 1
            
            # Print summary
            total_success = sum(
                len([r for r in results if r.get('status') == 'completed'])
                for results in agent_results.values()
            )
            total_errors = sum(
                len([r for r in results if r.get('status') == 'error'])
                for results in agent_results.values()
            )
            
            logger.info(f"Batch processing complete: {total_success} successful, {total_errors} errors")
            
            return agent_results
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            return {"error": [{"status": "error", "error": str(e)}]}
    
    def get_agent_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available agents and their capabilities."""
        capabilities = {}
        
        for agent_type, agent in self.agents.items():
            capabilities[agent_type] = {
                "supported_extensions": getattr(agent, 'supported_extensions', []),
                "description": agent.__class__.__doc__ or f"{agent_type.title()} processing agent",
                "available": True
            }
        
        return capabilities
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about agent processing capabilities."""
        stats = {
            "total_agents": len(self.agents),
            "agent_types": list(self.agents.keys()),
            "supported_extensions": []
        }
        
        # Collect all supported extensions
        for agent in self.agents.values():
            if hasattr(agent, 'supported_extensions'):
                stats["supported_extensions"].extend(agent.supported_extensions)
        
        # Remove duplicates and sort
        stats["supported_extensions"] = sorted(list(set(stats["supported_extensions"])))
        
        return stats


# Global instance
agent_manager = AgentManager()