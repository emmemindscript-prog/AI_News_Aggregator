"""
AI News Aggregator - Summarization Service
Uses LLM (GLM4.7 via OpenRouter) to summarize articles in Italian
"""

from dataclasses import dataclass
from typing import Optional

import openai

from app.core.config import get_settings


@dataclass
class SummaryResult:
    """Result from summarization"""
    summary: str
    language: str
    char_count: int
    tags: list[str]


class SummarizerService:
    """ LLM-powered summarization service"""
    
    SYSTEM_PROMPT_IT = """Sei un assistente AI specializzato in riassumere notizie tecnologiche.

TASK: Riassumi l'articolo in ITALIANO in 1-2 righe.

REGLA:
- Lingua: SOLO italiano
- Lunghezza: Massimo 280 caratteri
- Stile: Conciso, informativo, professionale
- Non menzionare la fonte o gli autori
- Focus su: contesto, impatto novità

Esempio input: "OpenAI releases GPT-5 with 16x context window and 50% cost reduction"
Esempio output: "OpenAI lancia GPT-5 con contesto 16x più ampio e costi ridotti del 50%. Major upgrade per applicazioni enterprise."

Esempio input: "New robotics startup Figure AI raises $675M for humanoid robots"
Esempio output: "Figure AI chiude round da 675M$ per robot umanoidi. Ambizione: automazione industriale entro 2026."

Rispondi ESATTAMENTE con il riassunto, niente altro."""

    SYSTEM_PROMPT_EN = """You are an AI news summarization assistant.

TASK: Summarize the article in 1-2 sentences.

RULES:
- Language: English
- Length: Maximum 280 characters
- Style: Concise, informative, professional
- Focus on: context, impact, key innovation

Respond with ONLY the summary."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = openai.AsyncOpenAI(
            api_key=self.settings.LLM_API_KEY,
            base_url=self.settings.LLM_BASE_URL
        )
        
    async def summarize(
        self,
        text: str,
        language: str = "it",
        max_chars: int = 280
    ) -> str:
        """
        Summarize text to max_chars length in target language
        
        Args:
            text: The content to summarize
            language: "it" or "en"
            max_chars: Maximum output length (default 280 for Telegram)
            
        Returns:
            Clean summary string
        """
        if not text or len(text.strip()) < 20:
            return text.strip() if text else "[No summary available]"
        
        # Truncate input to save tokens
        truncated = text[:2000].strip()
        
        system_prompt = self.SYSTEM_PROMPT_IT if language == "it" else self.SYSTEM_PROMPT_EN
        
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Articolo da riassumere:\n\n{truncated}\n\nRiassunto:"}
                ],
                temperature=self.settings.LLM_TEMPERATURE,
                max_tokens=150,
                timeout=30
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Post-process: ensure length and clean
            summary = self._clean_summary(summary)
            
            if len(summary) > max_chars:
                summary = summary[:max_chars-3] + "..."
                
            return summary
            
        except Exception as e:
            print(f"Summarization error: {e}")
            # Fallback: return truncated original
            return text[:max_chars-3] + "..." if len(text) > max_chars else text
    
    def _clean_summary(self, text: str) -> str:
        """Clean LLM output"""
        # Remove common prefixes
        for prefix in ['Riassunto:', 'Summary:', 'Ecco:', 'Ecco il riassunto:']:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                
        # Remove quotes if wrapped
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
            
        # Normalize whitespace
        text = " ".join(text.split())
        
        return text
