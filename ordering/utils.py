import uuid
from datetime import datetime
import threading
import time
import os

from .models import Order


def generate_order_number():
    return uuid.uuid4().hex[:8].upper()


def generate_receipt_number():
    return f"RCPT-{uuid.uuid4().hex[:8].upper()}"


def cart_total(cart_items):
    return sum(i['price'] * i['quantity'] for i in cart_items)


def now_iso():
    return datetime.utcnow().isoformat()


def _env_delays():
    def _get(name, default):
        try:
            return int(os.getenv(name, default))
        except Exception:
            return default
    return {
        'confirmed': _get('ORDER_DELAY_CONFIRMED', 3),
        'preparing': _get('ORDER_DELAY_PREPARING', 10),
        'ready': _get('ORDER_DELAY_READY', 20),
        'completed': _get('ORDER_DELAY_COMPLETED', 30),
    }


def _progress_order_status(order_id, delays=None):
    steps = ['confirmed', 'preparing', 'ready', 'completed']
    if delays is None:
        delays = _env_delays()
    speed = 1.0
    try:
        speed = float(os.getenv('ORDER_DELAY_SPEED', '1'))
        if speed <= 0:
            speed = 1.0
    except Exception:
        speed = 1.0
    try:
        order = Order.objects(id=order_id).first()
        if not order:
            return
        for status in steps:
            # If order was cancelled or already completed, stop automation
            order.reload()
            if order.status in ['cancelled', 'completed']:
                break
            # Sleep before moving to next status
            wait_s = max(0, int(delays.get(status, 5)))
            time.sleep(wait_s / speed)
            order.status = status
            order.updated_at = datetime.utcnow()
            order.save()
    finally:
        # Ensure flag is cleared when finished (optional: keep True to mark already automated)
        try:
            order = Order.objects(id=order_id).first()
            if order and order.status in ['cancelled', 'completed']:
                order.automation_started = True
                order.save()
        except Exception:
            pass


def start_order_automation(order):
    """Start background automation to progress an order's status.
    Safe to call multiple times; it will only start once per order."""
    if getattr(order, 'automation_started', False):
        return
    order.automation_started = True
    order.save()
    t = threading.Thread(target=_progress_order_status, args=(order.id,), daemon=True)
    t.start()
