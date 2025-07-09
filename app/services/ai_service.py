"""
AI Content Generation Service
Gemini 2.5 Flash integration for content generation
"""

import google.generativeai as genai
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import time
import json

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class AIService:
    """AI content generation service using Gemini 2.5 Flash"""
    
    def __init__(self):
        self.settings = get_settings()
        self._model = None
        self._initialize_genai()

    def _get_api_key_from_file(self) -> Optional[str]:
        """Read API key from settings.json"""
        try:
            with open("settings.json", 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            api_key = settings_data.get("gemini_api_key")
            return api_key if api_key and len(api_key) > 10 else None
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def _initialize_genai(self):
        """Initialize Gemini AI, prioritizing key from settings.json"""
        api_key = self._get_api_key_from_file() or self.settings.gemini_api_key
        
        if not api_key:
            logger.warning("⚠️ Gemini API key not set in settings.json or .env file")
            return
        
        try:
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(self.settings.default_ai_model)
            logger.info(f"✅ Gemini {self.settings.default_ai_model} initialized with key from {'settings file' if self._get_api_key_from_file() else '.env'}")
        except Exception as e:
            logger.error(f"❌ Gemini initialization failed: {e}")
            self._model = None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Gemini API connection"""
        if not self._model:
            return {
                "success": False,
                "error": "Gemini not initialized",
                "model": None
            }
        
        try:
            # Simple test prompt
            response = await self._generate_async("Test connection. Respond with 'OK'")
            return {
                "success": True,
                "model": self.settings.default_ai_model,
                "response": response[:50] if response else "No response",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": self.settings.default_ai_model
            }
    
    async def generate_content(
        self,
        topic_title: str,
        topic_content: str,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI content based on topic
        
        Args:
            topic_title: Original topic title
            topic_content: Original topic content/description
            custom_prompt: Custom prompt template (optional)
            
        Returns:
            Dict with generated content and metadata
        """
        if not self._model:
            return {
                "success": False,
                "error": "Gemini AI not available",
                "generated_content": "",
                "metadata": {}
            }
        
        start_time = time.time()
        
        try:
            # Build prompt
            prompt = self._build_prompt(topic_title, topic_content, custom_prompt)
            
            # Generate content
            generated_text = await self._generate_async(prompt)
            
            generation_time = time.time() - start_time
            
            return {
                "success": True,
                "generated_content": generated_text,
                "metadata": {
                    "model": self.settings.default_ai_model,
                    "prompt_used": prompt,
                    "generation_time_seconds": round(generation_time, 2),
                    "content_length": len(generated_text) if generated_text else 0,
                    "temperature": self.settings.ai_temperature,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ AI generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_content": "",
                "metadata": {
                    "generation_time_seconds": time.time() - start_time,
                    "error_timestamp": datetime.now().isoformat()
                }
            }
    
    def _build_prompt(
        self,
        title: str,
        content: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Build AI generation prompt"""
        
        if custom_prompt:
            base_prompt = custom_prompt
        else:
            # Load master prompt from file
            try:
                prompt_file_path = "ai_prompts/master_prompt.txt"
                with open(prompt_file_path, 'r', encoding='utf-8') as f:
                    base_prompt = f.read()
            except FileNotFoundError:
                logger.warning("Master prompt file not found, using default prompt")
                # Fallback to default prompt
                base_prompt = """
Sen bir psikoloji alanında uzman içerik üreticisisin. YouTube için kısa, etkileyici ve bilgilendirici videolar üretiyorsun.

Görevin: Verilen konuyu baz alarak, özgün ve ilgi çekici bir YouTube videosu scripti yazmak.

Video formatı:
- 30-60 saniye arası kısa video
- Hook (ilk 3 saniye çok önemli!)
- Ana mesaj (net ve anlaşılır)
- Call to action (beğen, yorum yap, takip et)
- Psikoloji temelli, pratik bilgiler
- Türkçe dilinde

Yazmana YASAK olanlar:
- Tıbbi tavsiye vermek
- Kesin tanı koymak
- İlaç önerisi
- Profesyonel terapi yerine geçen öneriler

Stil:
- Sade ve anlaşılır dil
- Günlük hayattan örnekler
- İzleyiciyle direkt konuşma
- Pozitif ve destekleyici ton

Verilen konu:
"""
        
        # Replace placeholder with actual content
        final_prompt = base_prompt.replace(
            "[BURAYA MÜŞTERİNİN WEB SİTESİNDEN SEÇTİĞİ KONU BAŞLIĞI GELECEK]", 
            f"**Başlık:** {title}\n\n**İçerik:** {content[:1000]}..."
        )
        
        return final_prompt
    
    async def _generate_async(self, prompt: str) -> str:
        """Generate content asynchronously"""
        if not self._model:
            raise Exception("Gemini model not initialized")
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def _sync_generate():
            response = self._model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.settings.ai_temperature,
                    max_output_tokens=self.settings.ai_max_tokens,
                )
            )
            return response.text if response.text else ""
        
        return await loop.run_in_executor(None, _sync_generate)
    
    def is_available(self) -> bool:
        """Check if AI service is available"""
        return self._model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        return {
            "model": self.settings.default_ai_model,
            "temperature": self.settings.ai_temperature,
            "max_tokens": self.settings.ai_max_tokens,
            "available": self.is_available()
        } 