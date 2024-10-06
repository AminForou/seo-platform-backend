
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ContactMessageSerializer
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ContactMessageView(APIView):
    def post(self, request):
        logger.info("Received data: %s", request.data)
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            # Send email notification
            name = serializer.validated_data['name']
            email = serializer.validated_data['email']
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            full_message = f"From: {name} <{email}>\n\n{message}"
            try:
                send_mail(
                    subject,
                    full_message,
                    settings.DEFAULT_FROM_EMAIL,  # Sender's email
                    [settings.CONTACT_EMAIL],     # Receiver's email
                    fail_silently=False,
                )
            except Exception as e:
                logger.error("Error sending email: %s", e)
                return Response({'error': 'Error sending email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'message': 'Message sent successfully!'}, status=status.HTTP_201_CREATED)
        else:
            logger.error("Form submission errors: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
