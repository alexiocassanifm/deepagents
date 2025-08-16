"""
Performance Optimizer - Ottimizzazione performance e rate limiting per LLM compression

Questo modulo implementa ottimizzazioni avanzate per gestire performance, rate limiting,
caching e scalabilità del sistema di compressione LLM.

Funzionalità principali:
1. Rate limiting intelligente con backoff esponenziale
2. Caching dei risultati di compressione
3. Pool di connessioni per chiamate parallele
4. Monitoring delle performance in tempo reale
5. Auto-tuning dei parametri basato su metriche
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum

import aiofiles
import aiofiles.os


class CacheStrategy(str, Enum):
    """Strategie di caching disponibili."""
    MEMORY = "memory"
    DISK = "disk"
    HYBRID = "hybrid"
    REDIS = "redis"


class PerformanceLevel(str, Enum):
    """Livelli di performance del sistema."""
    OPTIMAL = "optimal"
    GOOD = "good"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Metriche delle performance del sistema."""
    avg_compression_time: float = 0.0
    avg_token_throughput: float = 0.0
    cache_hit_rate: float = 0.0
    rate_limit_errors: int = 0
    timeouts: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    current_queue_size: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RateLimitConfig:
    """Configurazione rate limiting."""
    requests_per_minute: int = 20
    requests_per_hour: int = 1000
    burst_allowance: int = 5
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 300.0
    adaptive_adjustment: bool = True


class RateLimiter:
    """Rate limiter intelligente con backoff adattivo."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.minute_requests = deque()
        self.hour_requests = deque()
        self.backoff_time = 0.0
        self.consecutive_errors = 0
        self.last_request_time = 0.0
        
    async def acquire(self) -> bool:
        """Acquisisce permesso per una richiesta."""
        current_time = time.time()
        
        # Pulisce richieste vecchie
        self._cleanup_old_requests(current_time)
        
        # Controlla se dobbiamo aspettare per backoff
        if self.backoff_time > current_time:
            wait_time = self.backoff_time - current_time
            await asyncio.sleep(wait_time)
            return await self.acquire()  # Riprova dopo wait
        
        # Controlla limiti rate
        minute_count = len(self.minute_requests)
        hour_count = len(self.hour_requests)
        
        # Calcola allowance burst
        time_since_last = current_time - self.last_request_time
        burst_available = min(self.config.burst_allowance, max(0, time_since_last / 60))
        
        if (minute_count < self.config.requests_per_minute + burst_available and
            hour_count < self.config.requests_per_hour):
            
            # Permesso granted
            self.minute_requests.append(current_time)
            self.hour_requests.append(current_time)
            self.last_request_time = current_time
            self.consecutive_errors = 0  # Reset error count on success
            return True
        
        # Rate limit hit - calcola wait time
        if minute_count >= self.config.requests_per_minute:
            oldest_minute = self.minute_requests[0]
            wait_time = 60 - (current_time - oldest_minute)
        else:
            oldest_hour = self.hour_requests[0]
            wait_time = 3600 - (current_time - oldest_hour)
        
        await asyncio.sleep(max(1.0, wait_time))
        return await self.acquire()
    
    def _cleanup_old_requests(self, current_time: float):
        """Rimuove richieste vecchie dalle code."""
        minute_cutoff = current_time - 60
        hour_cutoff = current_time - 3600
        
        while self.minute_requests and self.minute_requests[0] < minute_cutoff:
            self.minute_requests.popleft()
        
        while self.hour_requests and self.hour_requests[0] < hour_cutoff:
            self.hour_requests.popleft()
    
    def handle_error(self, error_type: str = "rate_limit"):
        """Gestisce errore e aggiorna backoff."""
        self.consecutive_errors += 1
        
        if self.config.adaptive_adjustment:
            backoff_time = min(
                self.config.max_backoff_seconds,
                (self.config.backoff_multiplier ** self.consecutive_errors)
            )
            self.backoff_time = time.time() + backoff_time


class CompressionCache:
    """Cache per risultati di compressione con supporto persistenza."""
    
    def __init__(self, 
                 strategy: CacheStrategy = CacheStrategy.MEMORY,
                 max_memory_items: int = 1000,
                 cache_dir: str = "cache/compression",
                 ttl_seconds: int = 3600):
        self.strategy = strategy
        self.max_memory_items = max_memory_items
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        
        # Memory cache
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        
        # Stats
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "disk_reads": 0,
            "disk_writes": 0
        }
    
    def _generate_cache_key(self, messages: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        """Genera chiave cache basata su contenuto e configurazione."""
        # Include contenuto messaggi e configurazione compressione
        content = {
            "messages": messages,
            "config": config
        }
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    async def get(self, messages: List[Dict[str, Any]], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Recupera risultato dalla cache."""
        cache_key = self._generate_cache_key(messages, config)
        
        # Controlla memory cache
        if cache_key in self.memory_cache:
            cached_item = self.memory_cache[cache_key]
            
            # Controlla TTL
            if time.time() - cached_item["timestamp"] < self.ttl_seconds:
                self.access_times[cache_key] = time.time()
                self.stats["hits"] += 1
                return cached_item["data"]
            else:
                # Scaduto - rimuove
                del self.memory_cache[cache_key]
                del self.access_times[cache_key]
        
        # Controlla disk cache se disponibile
        if self.strategy in [CacheStrategy.DISK, CacheStrategy.HYBRID]:
            disk_result = await self._read_from_disk(cache_key)
            if disk_result:
                # Carica in memory per accesso futuro
                self.memory_cache[cache_key] = disk_result
                self.access_times[cache_key] = time.time()
                self.stats["hits"] += 1
                self.stats["disk_reads"] += 1
                return disk_result["data"]
        
        self.stats["misses"] += 1
        return None
    
    async def put(self, messages: List[Dict[str, Any]], config: Dict[str, Any], result: Dict[str, Any]):
        """Salva risultato in cache."""
        cache_key = self._generate_cache_key(messages, config)
        
        cached_item = {
            "data": result,
            "timestamp": time.time()
        }
        
        # Salva in memory
        self.memory_cache[cache_key] = cached_item
        self.access_times[cache_key] = time.time()
        
        # Gestisce eviction se necessario
        await self._evict_if_needed()
        
        # Salva su disk se configurato
        if self.strategy in [CacheStrategy.DISK, CacheStrategy.HYBRID]:
            await self._write_to_disk(cache_key, cached_item)
    
    async def _evict_if_needed(self):
        """Rimuove elementi vecchi se cache piena."""
        if len(self.memory_cache) > self.max_memory_items:
            # LRU eviction
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.memory_cache[oldest_key]
            del self.access_times[oldest_key]
            self.stats["evictions"] += 1
    
    async def _read_from_disk(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Legge da cache su disk."""
        try:
            file_path = f"{self.cache_dir}/{cache_key}.json"
            
            if await aiofiles.os.path.exists(file_path):
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    cached_item = json.loads(content)
                    
                    # Controlla TTL
                    if time.time() - cached_item["timestamp"] < self.ttl_seconds:
                        return cached_item
                    else:
                        # Scaduto - rimuove file
                        await aiofiles.os.remove(file_path)
        
        except Exception:
            pass  # Ignora errori di lettura
        
        return None
    
    async def _write_to_disk(self, cache_key: str, cached_item: Dict[str, Any]):
        """Scrive su cache disk."""
        try:
            # Crea directory se non esiste
            await aiofiles.os.makedirs(self.cache_dir, exist_ok=True)
            
            file_path = f"{self.cache_dir}/{cache_key}.json"
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(cached_item, default=str))
            
            self.stats["disk_writes"] += 1
        
        except Exception:
            pass  # Ignora errori di scrittura
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche cache."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": round(hit_rate, 2),
            "memory_items": len(self.memory_cache),
            "strategy": self.strategy.value
        }


class PerformanceMonitor:
    """Monitor delle performance in tempo reale."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.compression_times = deque(maxlen=window_size)
        self.token_throughputs = deque(maxlen=window_size)
        self.error_counts = defaultdict(int)
        self.start_time = time.time()
        
    def record_compression(self, processing_time: float, tokens_processed: int):
        """Registra una compressione completata."""
        self.compression_times.append(processing_time)
        
        if processing_time > 0:
            throughput = tokens_processed / processing_time
            self.token_throughputs.append(throughput)
    
    def record_error(self, error_type: str):
        """Registra un errore."""
        self.error_counts[error_type] += 1
    
    def get_current_performance(self) -> PerformanceMetrics:
        """Calcola metriche performance correnti."""
        avg_time = sum(self.compression_times) / len(self.compression_times) if self.compression_times else 0
        avg_throughput = sum(self.token_throughputs) / len(self.token_throughputs) if self.token_throughputs else 0
        
        total_errors = sum(self.error_counts.values())
        total_requests = len(self.compression_times) + total_errors
        
        return PerformanceMetrics(
            avg_compression_time=round(avg_time, 3),
            avg_token_throughput=round(avg_throughput, 1),
            rate_limit_errors=self.error_counts.get("rate_limit", 0),
            timeouts=self.error_counts.get("timeout", 0),
            total_requests=total_requests,
            successful_requests=len(self.compression_times),
            failed_requests=total_errors
        )
    
    def get_performance_level(self) -> PerformanceLevel:
        """Determina livello performance corrente."""
        metrics = self.get_current_performance()
        
        if metrics.total_requests == 0:
            return PerformanceLevel.OPTIMAL
        
        error_rate = metrics.failed_requests / metrics.total_requests
        avg_time = metrics.avg_compression_time
        
        if error_rate > 0.3 or avg_time > 60:
            return PerformanceLevel.CRITICAL
        elif error_rate > 0.15 or avg_time > 30:
            return PerformanceLevel.DEGRADED
        elif error_rate > 0.05 or avg_time > 15:
            return PerformanceLevel.GOOD
        else:
            return PerformanceLevel.OPTIMAL


class PerformanceOptimizer:
    """
    Ottimizzatore principale delle performance per compressione LLM.
    
    Coordina rate limiting, caching, monitoring e auto-tuning per
    ottimizzare throughput e ridurre latenza.
    """
    
    def __init__(self,
                 rate_limit_config: RateLimitConfig = None,
                 cache_strategy: CacheStrategy = CacheStrategy.HYBRID,
                 enable_auto_tuning: bool = True):
        
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.cache = CompressionCache(strategy=cache_strategy)
        self.monitor = PerformanceMonitor()
        self.enable_auto_tuning = enable_auto_tuning
        
        # Pool di task per compressioni parallele
        self.compression_semaphore = asyncio.Semaphore(3)  # Max 3 compressioni parallele
        self.compression_queue = asyncio.Queue(maxsize=10)
        
        # Auto-tuning parameters
        self.last_tuning = time.time()
        self.tuning_interval = 300  # 5 minuti
        
    async def optimized_compress(self,
                               compressor_func: Callable,
                               messages: List[Dict[str, Any]],
                               config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue compressione ottimizzata con caching, rate limiting e monitoring.
        
        Args:
            compressor_func: Funzione di compressione da chiamare
            messages: Messaggi da comprimere
            config: Configurazione compressione
        
        Returns:
            Risultato compressione (da cache o nuova chiamata)
        """
        start_time = time.time()
        
        try:
            # 1. Controlla cache prima
            cached_result = await self.cache.get(messages, config)
            if cached_result:
                # Cache hit - registra e restituisce
                self.monitor.record_compression(time.time() - start_time, cached_result.get("tokens_after", 0))
                return cached_result
            
            # 2. Acquisisce rate limit
            await self.rate_limiter.acquire()
            
            # 3. Acquisisce semaforo per controllo concorrenza
            async with self.compression_semaphore:
                # 4. Esegue compressione effettiva
                result = await compressor_func(messages, config)
                
                # 5. Salva in cache se successo
                if result.get("success", False):
                    await self.cache.put(messages, config, result)
                
                # 6. Registra metriche
                processing_time = time.time() - start_time
                tokens_processed = result.get("tokens_before", 0)
                self.monitor.record_compression(processing_time, tokens_processed)
                
                # 7. Auto-tuning se abilitato
                if self.enable_auto_tuning:
                    await self._auto_tune_if_needed()
                
                return result
        
        except asyncio.TimeoutError:
            self.monitor.record_error("timeout")
            self.rate_limiter.handle_error("timeout")
            raise
        
        except Exception as e:
            error_type = "rate_limit" if "rate" in str(e).lower() else "general"
            self.monitor.record_error(error_type)
            self.rate_limiter.handle_error(error_type)
            raise
    
    async def _auto_tune_if_needed(self):
        """Auto-tuning dei parametri basato su performance."""
        current_time = time.time()
        
        if current_time - self.last_tuning < self.tuning_interval:
            return
        
        self.last_tuning = current_time
        performance_level = self.monitor.get_performance_level()
        
        if performance_level == PerformanceLevel.CRITICAL:
            # Riduce carico - aumenta rate limit intervals
            self.rate_limiter.config.requests_per_minute = max(5, 
                int(self.rate_limiter.config.requests_per_minute * 0.7))
            
            # Riduce concorrenza
            if self.compression_semaphore._value > 1:
                # Crea nuovo semaforo con meno permits
                new_value = max(1, self.compression_semaphore._value - 1)
                self.compression_semaphore = asyncio.Semaphore(new_value)
        
        elif performance_level == PerformanceLevel.OPTIMAL:
            # Incrementa gradualmente capacità
            self.rate_limiter.config.requests_per_minute = min(50,
                int(self.rate_limiter.config.requests_per_minute * 1.1))
            
            # Aumenta concorrenza se stabile
            if self.compression_semaphore._value < 5:
                new_value = self.compression_semaphore._value + 1
                self.compression_semaphore = asyncio.Semaphore(new_value)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche complete del sistema."""
        performance_metrics = self.monitor.get_current_performance()
        performance_level = self.monitor.get_performance_level()
        cache_stats = self.cache.get_stats()
        
        return {
            "performance": {
                "level": performance_level.value,
                "metrics": performance_metrics.__dict__
            },
            "rate_limiting": {
                "config": self.rate_limiter.config.__dict__,
                "consecutive_errors": self.rate_limiter.consecutive_errors,
                "backoff_active": self.rate_limiter.backoff_time > time.time(),
                "current_backoff": max(0, self.rate_limiter.backoff_time - time.time())
            },
            "caching": cache_stats,
            "concurrency": {
                "max_parallel": self.compression_semaphore._value,
                "current_queue_size": self.compression_queue.qsize(),
                "auto_tuning_enabled": self.enable_auto_tuning
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check del sistema di ottimizzazione."""
        performance_level = self.monitor.get_performance_level()
        
        health_status = {
            "status": "healthy" if performance_level in [PerformanceLevel.OPTIMAL, PerformanceLevel.GOOD] else "degraded",
            "performance_level": performance_level.value,
            "issues": []
        }
        
        # Controlla issues specifici
        metrics = self.monitor.get_current_performance()
        
        if metrics.failed_requests / max(metrics.total_requests, 1) > 0.2:
            health_status["issues"].append("High error rate detected")
        
        if metrics.avg_compression_time > 30:
            health_status["issues"].append("High compression latency")
        
        if self.rate_limiter.consecutive_errors > 3:
            health_status["issues"].append("Rate limiting issues")
        
        cache_stats = self.cache.get_stats()
        if cache_stats["hit_rate"] < 20:
            health_status["issues"].append("Low cache efficiency")
        
        return health_status
