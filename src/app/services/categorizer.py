"""
AI News Aggregator - Categorization Service
Uses LLM (GLM4.7) to categorize articles
"""
from typing import Optional

import openai
from app.core.config import get_settings


class CategorizerService:
    """AI-powered article categorization"""
    
    CATEGORIES = {
        "ai-general": ["ai", "artificial intelligence", "generative ai", "gen ai"],
        "robotics": ["robot", "robotic", "humanoid", "automation"],
        "llm": ["llm", "large language model", "chatgpt", "gpt", "claude", "gemini"],
        "vibecoding": ["vibe coding", "ai coding", "copilot", "cursor", "code generation"],
        "openclaw": ["openclaw", "clawd", "agent framework"],
        "ethics": ["ai ethics", "ai safety", "alignment", "regulation"],
        "research": ["paper", "arxiv", "research", "benchmark", "study"]
    }
    
    SYSTEM_PROMPT = """Classifica l'articolo in UNA sola categoria tra:
- ai-general: notizie AI generiche
- robotics: robotica, automazione
- llm: modelli linguistici, GPT, ChatGPT
- vibecoding: coding con AI, Copilot
- openclaw: framework OpenClaw/Clawd
- ethics: etica AI, sicurezza, regolamentazione
- research: paper, ricerca accademica

Rispondi SOLO con il nome della categoria (senza spazi extra)."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def categorize(self, title: str, content: str) -> str:
        """Categorize article using keyword matching + LLM fallback"""
        # First try keyword matching
        combined = (title + " " + content).lower()
        
        for category, keywords in self.CATEGORIES.items():
            for kw in keywords:
                if kw in combined:
                    return category
        
        # Fallback to LLM categorization
        try:
            return await self._categorize_with_llm(title, content)
        except Exception:
            return "ai-general"
    
    async def _categorize_with_llm(self, title: str, content: str) -> str:
        """Use LLM to categorize"""
        text = f"{title}\n\n{content[:500]}"
        
        client = openai.AsyncOpenAI(
            api_key=self.settings.LLM_API_KEY,
            base_url=self.settings.LLM_BASE_URL
        )
        
        response = await client.chat.completions.create(
            model=self.settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=20
        )
        
        category = response.choices[0].message.content.strip().lower()
        
        # Normalize
        for valid in self.CATEGORIES.keys():
            if valid in category:
                return valid
        return "ai-general"
