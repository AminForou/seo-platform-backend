from rest_framework import serializers
from .models import ContactMessage

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'submitted_at']


class CSVFileSerializer(serializers.Serializer):
    file = serializers.FileField()



class RobotsTxtInputSerializer(serializers.Serializer):
    url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    content = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, data):
        url = data.get('url')
        content = data.get('content')
        if not url and not content:
            raise serializers.ValidationError("Either 'url' or 'content' must be provided.")
        return data

class RobotsTxtComparisonSerializer(serializers.Serializer):
    content1 = serializers.CharField(required=True)
    content2 = serializers.CharField(required=True)

class TestURLSerializer(serializers.Serializer):
    robots_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    robots_content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    test_urls = serializers.ListField(
        child=serializers.URLField(), required=True
    )
    user_agents = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )

    def validate(self, data):
        robots_url = data.get('robots_url')
        robots_content = data.get('robots_content')
        if not robots_url and not robots_content:
            raise serializers.ValidationError("Either 'robots_url' or 'robots_content' must be provided.")
        return data

class MultiRobotsTestSerializer(serializers.Serializer):
    robots_contents = serializers.ListField(
        child=serializers.CharField(), required=True
    )
    test_urls = serializers.ListField(
        child=serializers.URLField(), required=True
    )
    user_agents = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )