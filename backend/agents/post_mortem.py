"""
PostMortemAgent -- generates a structured post-mortem for a resolved incident
and adds the learnings back into the RAG knowledge base for future triage.
"""
import json
import logging
import pickle
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_KB_DIR = Path(__file__).parent.parent / "rag" / "knowledge_base" / "post_mortems"
_INDEX_PATH = Path(settings.faiss_index_path)

# Compact schema — same contract, ~40% fewer tokens than the original
SYSTEM_PROMPT = """You are a senior SRE writing a formal post-mortem.
Return ONLY valid JSON:
{
  "title": "concise title",
  "severity": "P1|P2|P3",
  "service": "...",
  "duration_minutes": 0,
  "timeline": [{"time":"...","event":"..."}],
  "confirmed_root_cause": "single sentence",
  "contributing_factors": ["..."],
  "impact": "customer/business impact",
  "resolution_summary": "what was done",
  "action_items": [{"priority":"High|Medium|Low","action":"...","owner":"...","due_days":7}],
  "lessons_learned": "2-3 sentences",
  "prevention_steps": ["..."]
}"""


@lru_cache(maxsize=1)
def _get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_deployment_name,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
        temperature=0,
        max_tokens=2000,
    )


class PostMortemAgent:
    """Generates post-mortems and feeds learnings back to the RAG index."""

    def __init__(self):
        self.llm = _get_llm()

    async def run(
        self,
        incident_id: str,
        triage_report: Dict[str, Any],
        resolution_summary: str,
        confirmed_root_cause: str,
        resolved_by: str = "On-Call Engineer",
    ) -> Dict[str, Any]:
        """Generate post-mortem, save it, and update the RAG index."""
        service     = triage_report.get("alert_summary", "").split("on ")[-1].split(" in")[0]
        alert_type  = triage_report.get("alert_summary", "")

        user_message = f"""
Incident ID: {incident_id}
Alert Summary: {alert_type}
Service: {service}
Resolved by: {resolved_by}

Triage Report Hypotheses:
{json.dumps(triage_report.get("root_cause_hypotheses", []), indent=2)}

Remediation Checklist:
{json.dumps(triage_report.get("remediation_checklist", []), indent=2)}

Operator-provided resolution: {resolution_summary}
Operator-confirmed root cause: {confirmed_root_cause}

Open tickets that were related:
{json.dumps(triage_report.get("open_tickets", []), indent=2)}

Generate the full post-mortem. Return ONLY valid JSON.
"""
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            post_mortem = json.loads(content)
        except Exception as exc:
            logger.error("[PostMortemAgent] LLM parse failed: %s", exc)
            post_mortem = {
                "title": f"Post-Mortem: {incident_id}",
                "severity": "P1",
                "service": service,
                "duration_minutes": None,
                "confirmed_root_cause": confirmed_root_cause,
                "resolution_summary": resolution_summary,
                "action_items": [],
                "lessons_learned": "See triage report for details.",
                "prevention_steps": [],
                "timeline": [],
                "contributing_factors": [],
                "impact": "See triage report.",
            }

        post_mortem["incident_id"] = incident_id
        post_mortem["generated_at"] = datetime.now(timezone.utc).isoformat()
        post_mortem["resolved_by"] = resolved_by

        # Save to knowledge base directory
        self._save_post_mortem(incident_id, post_mortem)

        # Update RAG index with learnings
        await self._update_rag(incident_id, post_mortem)

        logger.info("[PostMortemAgent] Post-mortem generated and saved for %s", incident_id)
        return post_mortem

    def _save_post_mortem(self, incident_id: str, post_mortem: Dict[str, Any]):
        _KB_DIR.mkdir(parents=True, exist_ok=True)
        out_path = _KB_DIR / f"{incident_id}.json"
        out_path.write_text(json.dumps(post_mortem, indent=2), encoding="utf-8")
        logger.info("[PostMortemAgent] Saved to %s", out_path)

    async def _update_rag(self, incident_id: str, post_mortem: Dict[str, Any]):
        """Incrementally add post-mortem learnings to the FAISS index."""
        try:
            import faiss
            from openai import AzureOpenAI

            # Build a rich text chunk from the post-mortem
            chunk = (
                f"POST-MORTEM {incident_id}: {post_mortem.get('title', '')} | "
                f"Service: {post_mortem.get('service', '')} | "
                f"Root Cause: {post_mortem.get('confirmed_root_cause', '')} | "
                f"Resolution: {post_mortem.get('resolution_summary', '')} | "
                f"Prevention: {'; '.join(post_mortem.get('prevention_steps', []))} | "
                f"Lessons: {post_mortem.get('lessons_learned', '')}"
            )

            client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            resp = client.embeddings.create(
                input=[chunk],
                model=settings.azure_openai_embedding_deployment,
            )
            embedding = np.array([resp.data[0].embedding], dtype=np.float32)

            index_file    = _INDEX_PATH / "index.faiss"
            metadata_file = _INDEX_PATH / "metadata.pkl"

            if not index_file.exists():
                logger.warning("[PostMortemAgent] FAISS index not found, skipping update")
                return

            index = faiss.read_index(str(index_file))
            with open(metadata_file, "rb") as f:
                metadata = pickle.load(f)

            index.add(embedding)
            metadata["texts"].append(chunk)
            metadata["sources"].append(f"post_mortem:{incident_id}")

            faiss.write_index(index, str(index_file))
            with open(metadata_file, "wb") as f:
                pickle.dump(metadata, f)

            logger.info("[PostMortemAgent] RAG index updated with %d total vectors", index.ntotal)
        except Exception as exc:
            logger.error("[PostMortemAgent] RAG update failed (non-fatal): %s", exc)
