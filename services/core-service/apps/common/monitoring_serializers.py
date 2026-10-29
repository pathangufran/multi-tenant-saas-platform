from rest_framework import serializers

class WorkerStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["available", "unavailable"]
    )
    workers = serializers.ListField(
        child=serializers.CharField()
    )

class BrokerStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["available", "unavailable", "unsupported"]
    )

class QueueDepthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["available", "unavailable", "unsupported"]
    )
    queues = serializers.DictField(
        child=serializers.IntegerField(min_value=0)
    )

class CeleryMonitoringSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["healthy", "degraded"]
    )
    broker = BrokerStatusSerializer()
    workers = WorkerStatusSerializer()
    queues = QueueDepthSerializer()
