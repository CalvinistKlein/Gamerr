"""
Error handling, logging, and rate limiting utilities for retro metadata scraper
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import sys


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, calls_per_second: float = 4.0, burst_size: int = 10):
        """
        Initialize rate limiter
        
        Args:
            calls_per_second: Maximum calls per second
            burst_size: Maximum burst size
        """
        self.calls_per_second = calls_per_second
        self.burst_size = burst_size
        self.min_interval = 1.0 / calls_per_second
        
        # Track call times
        self.call_times = []
        self.last_call_time = 0
        
        # Statistics
        self.total_calls = 0
        self.rate_limited_calls = 0
        self.start_time = time.time()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        current_time = time.time()
        
        # Remove old call times (older than 1 second)
        self.call_times = [t for t in self.call_times if current_time - t < 1.0]
        
        # Check if we're at burst limit
        if len(self.call_times) >= self.burst_size:
            # Wait until oldest call is more than 1 second ago
            oldest_time = self.call_times[0]
            wait_time = 1.0 - (current_time - oldest_time)
            if wait_time > 0:
                time.sleep(wait_time)
                self.rate_limited_calls += 1
                current_time = time.time()
        
        # Check minimum interval
        if self.last_call_time > 0:
            elapsed = current_time - self.last_call_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                time.sleep(wait_time)
                self.rate_limited_calls += 1
        
        # Record this call
        self.call_times.append(time.time())
        self.last_call_time = time.time()
        self.total_calls += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        current_time = time.time()
        duration = current_time - self.start_time
        
        return {
            'total_calls': self.total_calls,
            'rate_limited_calls': self.rate_limited_calls,
            'calls_per_second': self.total_calls / duration if duration > 0 else 0,
            'duration_seconds': duration,
            'current_rate_limit': self.calls_per_second
        }


class ErrorHandler:
    """Error handler with retry logic"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0,
                 exponential_backoff: bool = True):
        """
        Initialize error handler
        
        Args:
            max_retries: Maximum number of retries
            retry_delay: Initial retry delay in seconds
            exponential_backoff: Whether to use exponential backoff
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        
        # Statistics
        self.total_errors = 0
        self.retry_successes = 0
        self.retry_failures = 0
        self.error_counts = defaultdict(int)
    
    def retry_on_error(self, func: Callable) -> Callable:
        """Decorator for retrying functions on error"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(self.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # If this was a retry and succeeded
                    if attempt > 0:
                        self.retry_successes += 1
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    self.total_errors += 1
                    self.error_counts[type(e).__name__] += 1
                    
                    # Log error
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error in {func.__name__} (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                    
                    # Check if we should retry
                    if attempt < self.max_retries:
                        # Calculate delay
                        if self.exponential_backoff:
                            delay = self.retry_delay * (2 ** attempt)
                        else:
                            delay = self.retry_delay
                        
                        logger.info(f"Retrying in {delay:.1f} seconds...")
                        time.sleep(delay)
                    else:
                        self.retry_failures += 1
                        logger.error(f"Max retries exceeded for {func.__name__}")
                        raise
            
            # This should never be reached
            raise last_error
        
        return wrapper
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """Handle an error and return error information"""
        error_type = type(error).__name__
        error_message = str(error)
        
        self.total_errors += 1
        self.error_counts[error_type] += 1
        
        logger = logging.getLogger(__name__)
        logger.error(f"Error in {context}: {error_type}: {error_message}")
        
        return {
            'error_type': error_type,
            'error_message': error_message,
            'context': context,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error handler statistics"""
        return {
            'total_errors': self.total_errors,
            'retry_successes': self.retry_successes,
            'retry_failures': self.retry_failures,
            'error_counts': dict(self.error_counts)
        }


class ProgressTracker:
    """Track progress of long-running operations"""
    
    def __init__(self, total_items: int = 0, update_interval: int = 100):
        """
        Initialize progress tracker
        
        Args:
            total_items: Total number of items to process
            update_interval: How often to log progress (in items)
        """
        self.total_items = total_items
        self.update_interval = update_interval
        self.processed_items = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.last_log_count = 0
        
        # Statistics
        self.completed = False
        self.errors = 0
        self.skipped = 0
    
    def update(self, count: int = 1, error: bool = False, skipped: bool = False):
        """Update progress"""
        self.processed_items += count
        
        if error:
            self.errors += 1
        if skipped:
            self.skipped += 1
        
        # Log progress at intervals
        current_time = time.time()
        if (self.processed_items % self.update_interval == 0 or 
            current_time - self.last_log_time >= 5.0):  # Or every 5 seconds
            
            elapsed = current_time - self.start_time
            items_since_last = self.processed_items - self.last_log_count
            time_since_last = current_time - self.last_log_time
            
            rate = items_since_last / time_since_last if time_since_last > 0 else 0
            eta = None
            
            if self.total_items > 0 and rate > 0:
                remaining = self.total_items - self.processed_items
                eta_seconds = remaining / rate
                eta = timedelta(seconds=int(eta_seconds))
            
            logger = logging.getLogger(__name__)
            logger.info(
                f"Progress: {self.processed_items}/{self.total_items or '?'} "
                f"({self.get_percentage():.1f}%) | "
                f"Rate: {rate:.1f}/s | "
                f"Errors: {self.errors} | "
                f"Skipped: {self.skipped}"
                + (f" | ETA: {eta}" if eta else "")
            )
            
            self.last_log_time = current_time
            self.last_log_count = self.processed_items
    
    def complete(self):
        """Mark operation as complete"""
        self.completed = True
        
        elapsed = time.time() - self.start_time
        overall_rate = self.processed_items / elapsed if elapsed > 0 else 0
        
        logger = logging.getLogger(__name__)
        logger.info(
            f"Completed: {self.processed_items} items in {elapsed:.1f}s "
            f"({overall_rate:.1f}/s) | "
            f"Errors: {self.errors} | "
            f"Skipped: {self.skipped}"
        )
    
    def get_percentage(self) -> float:
        """Get completion percentage"""
        if self.total_items > 0:
            return (self.processed_items / self.total_items) * 100
        return 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get progress statistics"""
        elapsed = time.time() - self.start_time
        
        return {
            'processed_items': self.processed_items,
            'total_items': self.total_items,
            'percentage': self.get_percentage(),
            'elapsed_seconds': elapsed,
            'rate_per_second': self.processed_items / elapsed if elapsed > 0 else 0,
            'errors': self.errors,
            'skipped': self.skipped,
            'completed': self.completed
        }


def setup_logging(log_file: str = None, log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        log_file: Path to log file (optional)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Root logger
    """
    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress overly verbose loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return root_logger


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log execution time of a function"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(__name__)
        start_time = time.time()
        
        logger.debug(f"Starting {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"Completed {func.__name__} in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Failed {func.__name__} after {elapsed:.2f}s: {e}")
            raise
    
    return wrapper


class MemoryMonitor:
    """Monitor memory usage"""
    
    def __init__(self):
        try:
            import psutil
            self.psutil = psutil
            self.available = True
        except ImportError:
            self.psutil = None
            self.available = False
            logging.getLogger(__name__).warning("psutil not installed, memory monitoring disabled")
        
        self.start_memory = self.get_memory_usage() if self.available else None
    
    def get_memory_usage(self) -> Optional[Dict[str, float]]:
        """Get current memory usage in MB"""
        if not self.available:
            return None
        
        try:
            process = self.psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'percent': process.memory_percent()
            }
        except Exception:
            return None
    
    def log_memory_usage(self, context: str = ""):
        """Log current memory usage"""
        if not self.available:
            return
        
        memory = self.get_memory_usage()
        if memory:
            logger = logging.getLogger(__name__)
            logger.info(
                f"Memory usage {context}: "
                f"RSS: {memory['rss_mb']:.1f}MB, "
                f"VMS: {memory['vms_mb']:.1f}MB, "
                f"{memory['percent']:.1f}%"
            )
    
    def check_memory_limit(self, limit_mb: float = 1024) -> bool:
        """Check if memory usage exceeds limit"""
        if not self.available:
            return False
        
        memory = self.get_memory_usage()
        if memory and memory['rss_mb'] > limit_mb:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Memory usage ({memory['rss_mb']:.1f}MB) exceeds limit ({limit_mb}MB)"
            )
            return True
        
        return False


# Global instances for easy access
rate_limiter = RateLimiter(calls_per_second=4.0)
error_handler = ErrorHandler(max_retries=3)
memory_monitor = MemoryMonitor()