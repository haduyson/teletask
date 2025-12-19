"""
Prometheus Metrics
Export metrics in Prometheus format for monitoring
"""

import os
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import prometheus_client, make it optional
try:
    from prometheus_client import Counter, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, metrics will be basic text")

# Metrics storage (fallback when prometheus_client not available)
_metrics = {
    'tasks_created': 0,
    'tasks_completed': 0,
    'messages_received': 0,
    'messages_sent': 0,
    'errors': {},
    'uptime_start': time.time(),
    'memory_bytes': 0,
    'cpu_percent': 0,
}

if PROMETHEUS_AVAILABLE:
    # Create custom registry
    REGISTRY = CollectorRegistry()

    # Bot metrics
    BOT_UPTIME = Gauge(
        'bot_uptime_seconds',
        'Bot uptime in seconds',
        ['bot_name'],
        registry=REGISTRY
    )

    BOT_MEMORY = Gauge(
        'bot_memory_bytes',
        'Bot memory usage in bytes',
        ['bot_name'],
        registry=REGISTRY
    )

    BOT_CPU = Gauge(
        'bot_cpu_percent',
        'Bot CPU usage percentage',
        ['bot_name'],
        registry=REGISTRY
    )

    # Task metrics
    TASKS_CREATED = Counter(
        'tasks_created_total',
        'Total tasks created',
        ['bot_name'],
        registry=REGISTRY
    )

    TASKS_COMPLETED = Counter(
        'tasks_completed_total',
        'Total tasks completed',
        ['bot_name'],
        registry=REGISTRY
    )

    TASKS_OVERDUE = Gauge(
        'tasks_overdue_current',
        'Current overdue tasks',
        ['bot_name'],
        registry=REGISTRY
    )

    # Message metrics
    MESSAGES_RECEIVED = Counter(
        'messages_received_total',
        'Total messages received',
        ['bot_name'],
        registry=REGISTRY
    )

    MESSAGES_SENT = Counter(
        'messages_sent_total',
        'Total messages sent',
        ['bot_name'],
        registry=REGISTRY
    )

    # Error metrics
    ERRORS_TOTAL = Counter(
        'errors_total',
        'Total errors',
        ['bot_name', 'error_type'],
        registry=REGISTRY
    )


def get_bot_name() -> str:
    """Get bot name from environment."""
    return os.getenv('BOT_NAME', 'TeleTask')


def get_metrics_text() -> str:
    """Generate metrics text in Prometheus format."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest(REGISTRY).decode('utf-8')
    else:
        # Fallback: basic text format
        bot_name = get_bot_name()
        uptime = time.time() - _metrics['uptime_start']
        lines = [
            f"# HELP bot_uptime_seconds Bot uptime in seconds",
            f"# TYPE bot_uptime_seconds gauge",
            f'bot_uptime_seconds{{bot_name="{bot_name}"}} {uptime:.2f}',
            f"# HELP tasks_created_total Total tasks created",
            f"# TYPE tasks_created_total counter",
            f'tasks_created_total{{bot_name="{bot_name}"}} {_metrics["tasks_created"]}',
            f"# HELP tasks_completed_total Total tasks completed",
            f"# TYPE tasks_completed_total counter",
            f'tasks_completed_total{{bot_name="{bot_name}"}} {_metrics["tasks_completed"]}',
            f"# HELP messages_received_total Total messages received",
            f"# TYPE messages_received_total counter",
            f'messages_received_total{{bot_name="{bot_name}"}} {_metrics["messages_received"]}',
            f"# HELP bot_memory_bytes Bot memory usage",
            f"# TYPE bot_memory_bytes gauge",
            f'bot_memory_bytes{{bot_name="{bot_name}"}} {_metrics["memory_bytes"]}',
        ]
        return '\n'.join(lines)


def record_task_created():
    """Record task creation."""
    bot_name = get_bot_name()
    if PROMETHEUS_AVAILABLE:
        TASKS_CREATED.labels(bot_name=bot_name).inc()
    else:
        _metrics['tasks_created'] += 1


def record_task_completed():
    """Record task completion."""
    bot_name = get_bot_name()
    if PROMETHEUS_AVAILABLE:
        TASKS_COMPLETED.labels(bot_name=bot_name).inc()
    else:
        _metrics['tasks_completed'] += 1


def record_message_received():
    """Record message received."""
    bot_name = get_bot_name()
    if PROMETHEUS_AVAILABLE:
        MESSAGES_RECEIVED.labels(bot_name=bot_name).inc()
    else:
        _metrics['messages_received'] += 1


def record_message_sent():
    """Record message sent."""
    bot_name = get_bot_name()
    if PROMETHEUS_AVAILABLE:
        MESSAGES_SENT.labels(bot_name=bot_name).inc()
    else:
        _metrics['messages_sent'] += 1


def record_error(error_type: str):
    """Record error occurrence."""
    bot_name = get_bot_name()
    if PROMETHEUS_AVAILABLE:
        ERRORS_TOTAL.labels(bot_name=bot_name, error_type=error_type).inc()
    else:
        _metrics['errors'][error_type] = _metrics['errors'].get(error_type, 0) + 1


def update_system_metrics(uptime: float, memory: float, cpu: float):
    """Update system resource metrics."""
    bot_name = get_bot_name()
    if PROMETHEUS_AVAILABLE:
        BOT_UPTIME.labels(bot_name=bot_name).set(uptime)
        BOT_MEMORY.labels(bot_name=bot_name).set(memory)
        BOT_CPU.labels(bot_name=bot_name).set(cpu)
    else:
        _metrics['memory_bytes'] = memory
        _metrics['cpu_percent'] = cpu


def update_overdue_tasks(count: int):
    """Update overdue tasks count."""
    bot_name = get_bot_name()
    if PROMETHEUS_AVAILABLE:
        TASKS_OVERDUE.labels(bot_name=bot_name).set(count)
