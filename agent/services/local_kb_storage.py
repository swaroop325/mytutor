"""
Local Knowledge Base Storage Service
Provides local file-based storage for agent processing results to avoid AgentCore Memory throttling.
Uses the same data directory as the backend service for consistency.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class LocalKBStorage:
    """Local file-based knowledge base storage to avoid memory throttling."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize local storage with configurable data directory."""
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Use backend data directory by default
            project_root = Path(__file__).parent.parent.parent
            self.data_dir = project_root / "backend" / "data"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.kb_results_dir = self.data_dir / "kb_results"
        self.kb_results_dir.mkdir(exist_ok=True)

        logger.info(f"Local KB storage initialized at: {self.data_dir}")

    def save_agent_results(
        self,
        kb_id: str,
        agent_type: str,
        results: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save agent processing results to local file storage.

        Args:
            kb_id: Knowledge base ID
            agent_type: Type of agent (text, pdf, audio, video, image)
            results: Processing results from the agent
            metadata: Optional metadata (file info, timestamps, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create KB directory
            kb_dir = self.kb_results_dir / kb_id
            kb_dir.mkdir(exist_ok=True)

            # Save agent results
            result_file = kb_dir / f"{agent_type}_results.json"

            data = {
                "kb_id": kb_id,
                "agent_type": agent_type,
                "timestamp": datetime.utcnow().isoformat(),
                "results": results,
                "metadata": metadata or {}
            }

            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Saved {agent_type} results for KB {kb_id}")
            logger.info(f"📁 Storage path: {result_file.absolute()}")
            return True

        except Exception as e:
            logger.error(f"Failed to save {agent_type} results for KB {kb_id}: {e}")
            return False

    def load_agent_results(
        self,
        kb_id: str,
        agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load agent processing results from local storage.

        Args:
            kb_id: Knowledge base ID
            agent_type: Specific agent type to load, or None for all agents

        Returns:
            Dictionary with agent results
        """
        try:
            kb_dir = self.kb_results_dir / kb_id

            logger.info(f"🔍 Looking for KB results in: {kb_dir.absolute()}")

            if not kb_dir.exists():
                logger.warning(f"❌ No local storage directory found for KB {kb_id}")
                logger.warning(f"Expected path: {kb_dir.absolute()}")
                return {}

            # Load specific agent or all agents
            if agent_type:
                result_file = kb_dir / f"{agent_type}_results.json"
                if result_file.exists():
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get("results", {})
                return {}
            else:
                # Load all agent results
                all_results = {}
                for result_file in kb_dir.glob("*_results.json"):
                    agent_name = result_file.stem.replace("_results", "")
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        all_results[agent_name] = data.get("results", {})

                logger.info(f"Loaded results for {len(all_results)} agents from KB {kb_id}")
                return all_results

        except Exception as e:
            logger.error(f"Failed to load results for KB {kb_id}: {e}")
            return {}

    def save_comprehensive_analysis(
        self,
        kb_id: str,
        analysis: str
    ) -> bool:
        """Save comprehensive analysis to local storage."""
        try:
            kb_dir = self.kb_results_dir / kb_id
            kb_dir.mkdir(exist_ok=True)

            analysis_file = kb_dir / "comprehensive_analysis.txt"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write(analysis)

            logger.info(f"Saved comprehensive analysis for KB {kb_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save comprehensive analysis for KB {kb_id}: {e}")
            return False

    def load_comprehensive_analysis(self, kb_id: str) -> Optional[str]:
        """Load comprehensive analysis from local storage."""
        try:
            kb_dir = self.kb_results_dir / kb_id
            analysis_file = kb_dir / "comprehensive_analysis.txt"

            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    return f.read()

            logger.warning(f"No comprehensive analysis found for KB {kb_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to load comprehensive analysis for KB {kb_id}: {e}")
            return None

    def save_training_content(
        self,
        kb_id: str,
        training_content: Dict[str, Any]
    ) -> bool:
        """Save training content to local storage."""
        try:
            kb_dir = self.kb_results_dir / kb_id
            kb_dir.mkdir(exist_ok=True)

            training_file = kb_dir / "training_content.json"
            with open(training_file, 'w', encoding='utf-8') as f:
                json.dump(training_content, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved training content for KB {kb_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save training content for KB {kb_id}: {e}")
            return False

    def load_training_content(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """Load training content from local storage."""
        try:
            kb_dir = self.kb_results_dir / kb_id
            training_file = kb_dir / "training_content.json"

            if training_file.exists():
                with open(training_file, 'r', encoding='utf-8') as f:
                    return json.load(f)

            logger.warning(f"No training content found for KB {kb_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to load training content for KB {kb_id}: {e}")
            return None

    def get_kb_summary(self, kb_id: str) -> Dict[str, Any]:
        """Get summary information about a knowledge base."""
        try:
            kb_dir = self.kb_results_dir / kb_id

            if not kb_dir.exists():
                return {"exists": False}

            # Count agent results
            agent_files = list(kb_dir.glob("*_results.json"))
            agent_types = [f.stem.replace("_results", "") for f in agent_files]

            # Check for other files
            has_analysis = (kb_dir / "comprehensive_analysis.txt").exists()
            has_training = (kb_dir / "training_content.json").exists()

            return {
                "exists": True,
                "kb_id": kb_id,
                "agent_types": agent_types,
                "agent_count": len(agent_types),
                "has_comprehensive_analysis": has_analysis,
                "has_training_content": has_training,
                "storage_path": str(kb_dir)
            }

        except Exception as e:
            logger.error(f"Failed to get KB summary for {kb_id}: {e}")
            return {"exists": False, "error": str(e)}

    def delete_kb(self, kb_id: str) -> bool:
        """Delete all local storage for a knowledge base."""
        try:
            kb_dir = self.kb_results_dir / kb_id

            if kb_dir.exists():
                import shutil
                shutil.rmtree(kb_dir)
                logger.info(f"Deleted local storage for KB {kb_id}")
                return True

            logger.warning(f"No local storage found for KB {kb_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to delete KB {kb_id}: {e}")
            return False

    def list_all_kbs(self) -> List[str]:
        """List all knowledge base IDs in local storage."""
        try:
            kb_dirs = [d.name for d in self.kb_results_dir.iterdir() if d.is_dir()]
            logger.info(f"Found {len(kb_dirs)} knowledge bases in local storage")
            return kb_dirs
        except Exception as e:
            logger.error(f"Failed to list KBs: {e}")
            return []


# Global instance
local_kb_storage = LocalKBStorage()
