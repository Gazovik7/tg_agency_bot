import asyncio
import logging
import os
from typing import Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Sentiment analysis using OpenRouter API with Mistral model"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "mistralai/mistral-7b-instruct"
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not found, sentiment analysis will be disabled")
    
    async def analyze_sentiment(self, text: str) -> Optional[Dict]:
        """
        Analyze sentiment of given text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with keys: score (-1 to 1), label (positive/negative/neutral), confidence (0-1)
        """
        if not self.api_key:
            logger.warning("No API key available for sentiment analysis")
            return None
        
        if not text or len(text.strip()) < 3:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0}
        
        try:
            prompt = self._create_sentiment_prompt(text)
            response = await self._call_openrouter_api(prompt)
            
            if response:
                return self._parse_sentiment_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
        
        return None
    
    def _create_sentiment_prompt(self, text: str) -> str:
        """Create prompt for sentiment analysis"""
        return f"""Analyze the sentiment of the following message and respond with ONLY a JSON object in this exact format:
{{"score": <float between -1 and 1>, "label": "<positive|negative|neutral>", "confidence": <float between 0 and 1>}}

Rules:
- score: -1 (very negative) to 1 (very positive), 0 is neutral
- label: "positive", "negative", or "neutral"
- confidence: how confident you are in the analysis (0-1)
- Consider context of customer service communication
- Response must be valid JSON only

Message to analyze:
"{text[:500]}"

JSON Response:"""
    
    async def _call_openrouter_api(self, prompt: str) -> Optional[str]:
        """Call OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": "Customer Service Monitor"  # Optional
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 100,
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error {response.status}: {error_text}")
                        return None
        
        except asyncio.TimeoutError:
            logger.error("OpenRouter API timeout")
            return None
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            return None
    
    def _parse_sentiment_response(self, response: str) -> Optional[Dict]:
        """Parse sentiment analysis response"""
        try:
            import json
            
            # Clean response - sometimes the model adds extra text
            response = response.strip()
            
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx + 1]
                result = json.loads(json_str)
                
                # Validate required fields
                if all(key in result for key in ["score", "label", "confidence"]):
                    # Ensure score is within bounds
                    score = max(-1.0, min(1.0, float(result["score"])))
                    
                    # Ensure confidence is within bounds
                    confidence = max(0.0, min(1.0, float(result["confidence"])))
                    
                    # Validate label
                    label = result["label"].lower()
                    if label not in ["positive", "negative", "neutral"]:
                        # Infer label from score if invalid
                        if score > 0.1:
                            label = "positive"
                        elif score < -0.1:
                            label = "negative"
                        else:
                            label = "neutral"
                    
                    return {
                        "score": score,
                        "label": label,
                        "confidence": confidence
                    }
        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing sentiment response: {e}, response: {response}")
        
        return None
    
    async def analyze_batch(self, texts: list) -> list:
        """Analyze sentiment for multiple texts"""
        tasks = [self.analyze_sentiment(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        return [result for result in results if isinstance(result, dict)]


# Example usage
async def test_sentiment_analyzer():
    """Test function for sentiment analyzer"""
    analyzer = SentimentAnalyzer()
    
    test_messages = [
        "I'm very happy with your service!",
        "This is terrible, I want a refund",
        "Hello, I have a question about my order",
        "Thank you for your help",
        "This doesn't work at all, I'm frustrated"
    ]
    
    for message in test_messages:
        result = await analyzer.analyze_sentiment(message)
        print(f"Text: {message}")
        print(f"Result: {result}")
        print("---")


if __name__ == "__main__":
    asyncio.run(test_sentiment_analyzer())
