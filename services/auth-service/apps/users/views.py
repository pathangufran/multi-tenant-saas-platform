from rest_framework import status
from rest_framework.views import APIView   
from rest_framework.response import Response
from .serializers import (
    UserRegistrationSerializer,
    UserRegistrationResponseSerializer,
)
from .services import UserService

class UserRegistrationView(APIView):

    def post(self,request):
        serializer = UserRegistrationSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        user = UserService.register_user(
            **serializer.validated_data,
        )
        response = UserRegistrationResponseSerializer(
            user
        )

        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )

    