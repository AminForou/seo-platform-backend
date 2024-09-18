from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests

@api_view(['POST'])
def check_url_status(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL is required.'}, status=400)
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return Response({'status_code': response.status_code})
    except requests.exceptions.RequestException as e:
        return Response({"error": str(e)}, status=400)
