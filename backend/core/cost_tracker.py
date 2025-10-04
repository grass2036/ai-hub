import json
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import tiktoken
from dataclasses import dataclass, asdict
from enum import Enum

class ServiceType(str, Enum):
    OPENROUTER = "openrouter"
    GEMINI = "gemini"

@dataclass
class UsageRecord:
    timestamp: str
    service: ServiceType
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    request_id: str = ""
    
    def to_dict(self):
        return asdict(self)

class CostTracker:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.usage_file = self.data_dir / "usage_stats.json"
        self.daily_stats_file = self.data_dir / "daily_stats.json"
        
        # OpenRouter pricing (per 1M tokens)
        self.openrouter_pricing = {
            "x-ai/grok-beta": {"input": 5.0, "output": 15.0},
            "x-ai/grok-2-vision-1212": {"input": 2.0, "output": 10.0},
            "x-ai/grok-4-fast:free": {"input": 0.0, "output": 0.0},
            "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
            "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},
            "google/gemini-pro": {"input": 1.25, "output": 5.0},
            "anthropic/claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
            "openai/gpt-4o": {"input": 2.5, "output": 10.0},
            "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "meta-llama/llama-3.1-8b-instruct:free": {"input": 0.0, "output": 0.0},
            "huggingface/qwen2.5-72b-instruct": {"input": 0.56, "output": 2.24},
        }
        
        # Gemini pricing (per 1M tokens)
        self.gemini_pricing = {
            "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
            "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
            "gemini-1.0-pro": {"input": 0.50, "output": 1.50},
        }
        
        # Initialize tokenizer for accurate counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback approximation
            return int(len(text.split()) * 1.3)
    
    def estimate_cost(self, service: ServiceType, model: str, 
                     input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on service, model and token usage"""
        if service == ServiceType.OPENROUTER:
            pricing = self.openrouter_pricing.get(model, {"input": 1.0, "output": 3.0})
        elif service == ServiceType.GEMINI:
            pricing = self.gemini_pricing.get(model, {"input": 0.5, "output": 1.5})
        else:
            pricing = {"input": 1.0, "output": 3.0}
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return round(input_cost + output_cost, 6)
    
    async def track_usage(self, service: ServiceType, model: str, 
                         input_text: str, output_text: str, 
                         request_id: str = "") -> UsageRecord:
        """Track a single API usage"""
        input_tokens = int(self.count_tokens(input_text))
        output_tokens = int(self.count_tokens(output_text))
        total_tokens = input_tokens + output_tokens
        
        estimated_cost = self.estimate_cost(service, model, input_tokens, output_tokens)
        
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            service=service,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            request_id=request_id
        )
        
        await self._save_usage_record(record)
        await self._update_daily_stats(record)
        
        return record
    
    async def _save_usage_record(self, record: UsageRecord):
        """Save usage record to file"""
        try:
            if self.usage_file.exists():
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"records": []}
            
            data["records"].append(record.to_dict())
            
            # Keep only last 1000 records to prevent file from growing too large
            if len(data["records"]) > 1000:
                data["records"] = data["records"][-1000:]
            
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving usage record: {e}")
    
    async def _update_daily_stats(self, record: UsageRecord):
        """Update daily statistics"""
        try:
            today = date.today().isoformat()
            
            if self.daily_stats_file.exists():
                with open(self.daily_stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            if today not in data:
                data[today] = {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "services": {},
                    "models": {}
                }
            
            day_stats = data[today]
            day_stats["total_requests"] += 1
            day_stats["total_tokens"] += record.total_tokens
            day_stats["total_cost"] += record.estimated_cost_usd
            
            # Service stats
            service_key = str(record.service)
            if service_key not in day_stats["services"]:
                day_stats["services"][service_key] = {
                    "requests": 0, "tokens": 0, "cost": 0.0
                }
            
            day_stats["services"][service_key]["requests"] += 1
            day_stats["services"][service_key]["tokens"] += record.total_tokens
            day_stats["services"][service_key]["cost"] += record.estimated_cost_usd
            
            # Model stats
            if record.model not in day_stats["models"]:
                day_stats["models"][record.model] = {
                    "requests": 0, "tokens": 0, "cost": 0.0
                }
            
            day_stats["models"][record.model]["requests"] += 1
            day_stats["models"][record.model]["tokens"] += record.total_tokens
            day_stats["models"][record.model]["cost"] += record.estimated_cost_usd
            
            with open(self.daily_stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error updating daily stats: {e}")
    
    async def get_daily_stats(self, target_date: Optional[str] = None) -> Dict:
        """Get statistics for a specific date"""
        if target_date is None:
            target_date = date.today().isoformat()
        
        try:
            if self.daily_stats_file.exists():
                with open(self.daily_stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get(target_date, {})
        except Exception as e:
            print(f"Error reading daily stats: {e}")
        
        return {}
    
    async def get_recent_usage(self, limit: int = 50) -> List[Dict]:
        """Get recent usage records"""
        try:
            if self.usage_file.exists():
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                records = data.get("records", [])
                return records[-limit:] if records else []
        except Exception as e:
            print(f"Error reading usage records: {e}")
        
        return []
    
    async def get_cost_summary(self, days: int = 30) -> Dict:
        """Get cost summary for the last N days"""
        try:
            if not self.daily_stats_file.exists():
                return {"total_cost": 0.0, "total_tokens": 0, "total_requests": 0, "daily_breakdown": []}
            
            with open(self.daily_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get last N days
            from datetime import timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)
            
            total_cost = 0.0
            total_tokens = 0
            total_requests = 0
            daily_breakdown = []
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.isoformat()
                day_data = data.get(date_str, {})
                
                day_cost = day_data.get("total_cost", 0.0)
                day_tokens = day_data.get("total_tokens", 0)
                day_requests = day_data.get("total_requests", 0)
                
                total_cost += day_cost
                total_tokens += day_tokens
                total_requests += day_requests
                
                daily_breakdown.append({
                    "date": date_str,
                    "cost": day_cost,
                    "tokens": day_tokens,
                    "requests": day_requests
                })
                
                current_date += timedelta(days=1)
            
            return {
                "total_cost": round(total_cost, 4),
                "total_tokens": total_tokens,
                "total_requests": total_requests,
                "daily_breakdown": daily_breakdown,
                "period_days": days
            }
            
        except Exception as e:
            print(f"Error calculating cost summary: {e}")
            return {"total_cost": 0.0, "total_tokens": 0, "total_requests": 0, "daily_breakdown": []}