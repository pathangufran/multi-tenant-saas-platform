from rest_framework import serializers

class LivenessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["alive"],
    )
    service = serializers.CharField()
    timestamp = serializers.DateTimeField()
    
class ReadinessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["ready","not_ready"]
    )
    service = serializers.CharField()
    timestamp = serializers.DateTimeField()
    checks = serializers.DictField(
        child=serializers.ChoiceField(
            choices=["ok","unavailable"]
        )
    )
    