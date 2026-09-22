"""Agent debate orchestration.

Multi-agent collaborative discussion with turn-based loop and final synthesis.

Flow:
1. User prompt → Agent A responds
2. Agent B reads full history + A's response → critiques/complements
3. Agent A reads B → responds
4. Repeat for N rounds or convergence
5. Synthesizer agent produces final consolidated answer

This module reuses stream_agent_loop for each participant and manages
message history, round limits, and convergence detection.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

from src.agent_loop import stream_agent_loop
from src.constants import APP_VERSION

logger = logging.getLogger(__name__)

DEFAULT_DEBATE_ROUNDS = 3
DEFAULT_AGENTS = ["Analyste", "Critique", "Synthétiseur"]

def build_system_prompt(role: str, round_num: int = 1) -> str:
    if role == "Analyste":
        return (
            "Tu es l'Analyste. Ton rôle est d'explorer le problème, proposer des solutions "
            "et apporter des faits. Sois précis, structuré et cite tes hypothèses. "
            f"Tour de discussion {round_num}."
        )
    if role == "Critique":
        return (
            "Tu es le Critique. Ton rôle est de challenger l'analyse précédente, pointer les lacunes, "
            "proposer des contre-exemples et améliorer la robustesse. Sois constructif mais exigeant. "
            f"Tour de discussion {round_num}."
        )
    if role == "Synthétiseur":
        return (
            "Tu es le Synthétiseur. Ton rôle est de lire l'ensemble de la discussion et produire "
            "une réponse finale consolidée, claire et actionnable. Résume les convergences, "
            "les divergences majeures et donne une recommandation finale."
        )
    return "Tu es un assistant aide."

async def _run_single_agent(
    endpoint_url: str,
    model: str,
    messages: List[Dict],
    role: str,
    round_num: int,
    **kwargs,
) -> str:
    """Run one agent turn and return accumulated text."""
    system_prompt = build_system_prompt(role, round_num)
    # Prepend system prompt
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    full_text = ""
    async for chunk in stream_agent_loop(
        endpoint_url=endpoint_url,
        model=model,
        messages=full_messages,
        **kwargs
    ):
        if chunk.startswith("data: "):
            try:
                import json
                data = json.loads(chunk[6:])
                if "delta" in data and not data.get("thinking"):
                    full_text += data["delta"]
            except Exception:
                pass
    return full_text

async def stream_debate(
    endpoint_url: str,
    model: str,
    user_messages: List[Dict],
    *,
    rounds: int = DEFAULT_DEBATE_ROUNDS,
    agents: Optional[List[str]] = None,
    **kwargs,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream a multi-agent debate.

    Yields dicts:
    - {type: "turn_start", role, round}
    - {type: "delta", role, round, text}
    - {type: "turn_end", role, round}
    - {type: "synthesis", text}
    """
    agents = agents or DEFAULT_AGENTS
    # Ensure last two are Critique and Synthétiseur for simplicity
    history = list(user_messages)

    # Initial analyst turn
    for r in range(1, rounds + 1):
        for idx, role in enumerate(agents[:-1]):  # all but synthesizer
            yield {"type": "turn_start", "role": role, "round": r}
            text = await _run_single_agent(
                endpoint_url, model, history, role, r, **kwargs
            )
            # Stream simulated deltas
            # For simplicity, emit whole text as one delta
            yield {"type": "delta", "role": role, "round": r, "text": text}
            yield {"type": "turn_end", "role": role, "round": r}
            # Append to history
            history.append({"role": "assistant", "content": f"[{role} Tour {r}]\n{text}"})
            # Alternate agents
            # Continue loop

    # Final synthesis
    synthesizer_role = agents[-1]
    yield {"type": "turn_start", "role": synthesizer_role, "round": rounds + 1}
    synthesis_text = await _run_single_agent(
        endpoint_url, model, history, synthesizer_role, rounds + 1, **kwargs
    )
    yield {"type": "delta", "role": synthesizer_role, "round": rounds + 1, "text": synthesis_text}
    yield {"type": "synthesis", "text": synthesis_text}
    yield {"type": "turn_end", "role": synthesizer_role, "round": rounds + 1}
