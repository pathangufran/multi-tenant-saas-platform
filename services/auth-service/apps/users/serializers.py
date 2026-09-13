from rest_framework import serializers
from django.core.validators import validate_email
from rest_framework.validators import ValidationError

class UserRegistrationSerializer(
    serializers.Serializer
):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )
    first_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    last_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    def validate_email(self,value):
        try:
            validate_email(value)

        except ValidationError:
            raise ValidationError(
                "Please enter a valid email."
            )

        return value.lower().strip()

    def validate_password(self,value):
        if value != value.strip():
            raise ValidationError(
                "Password cannot start or " \
                "end with whitespace."
            )

        return value

class UserRegistrationResponseSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    