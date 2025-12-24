from datetime import timedelta


class PriorityHandler:
    """Service for handling notification priority logic"""

    PRIORITY_CONFIG = {
        'high': {
            'ttl': timedelta(hours=1),
            'delivery_mode': 'immediate',
        },
        'medium': {
            'ttl': timedelta(days=1),
            'delivery_mode': 'normal',
        },
        'low': {
            'ttl': timedelta(days=7),
            'delivery_mode': 'batch',
        }
    }

    @classmethod
    def get_ttl(cls, priority):
        """Get time-to-live for a priority level"""
        return cls.PRIORITY_CONFIG.get(priority, cls.PRIORITY_CONFIG['medium'])['ttl']

    @classmethod
    def get_delivery_mode(cls, priority):
        """Get delivery mode for a priority level"""
        return cls.PRIORITY_CONFIG.get(priority, cls.PRIORITY_CONFIG['medium'])['delivery_mode']

    @classmethod
    def should_deliver_immediately(cls, priority):
        """Check if notification should be delivered immediately"""
        return cls.get_delivery_mode(priority) == 'immediate'

    @classmethod
    def should_batch(cls, priority):
        """Check if notification should be batched"""
        return cls.get_delivery_mode(priority) == 'batch'
