from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.urls import reverse

@api_view(['GET', 'POST'])
def check_url_status(request):
    url = request.GET.get('url') if request.method == 'GET' else request.data.get('url')
    user_agent = request.GET.get('user_agent') if request.method == 'GET' else request.data.get('user_agent')
    if not user_agent:
        user_agent = request.META.get('HTTP_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                         'Chrome/115.0.0.0 Safari/537.36')
    if not url:
        return Response({'error': 'URL is required.'}, status=400)
    try:
        start_time = time.time()

        # Initialize variables
        redirect_steps = []
        current_url = url
        headers = {'User-Agent': user_agent}
        current_response = requests.get(current_url, headers=headers, allow_redirects=False, timeout=10)
        current_status_code = current_response.status_code

        # Record initial step
        redirect_steps.append({
            'url': current_url,
            'status_code': current_status_code
        })

        # Follow redirects manually to build the steps
        while current_response.is_redirect:
            next_url = current_response.headers.get('Location')
            if not next_url:
                break
            # Handle relative URLs
            next_url = urljoin(current_url, next_url)

            # Request next URL
            current_url = next_url
            current_response = requests.get(current_url, headers=headers, allow_redirects=False, timeout=10)
            current_status_code = current_response.status_code

            # Record the step
            redirect_steps.append({
                'url': current_url,
                'status_code': current_status_code
            })

        # Now current_response is the final response
        final_url = current_url
        final_status_code = current_status_code
        response_time = time.time() - start_time

        # Parse the final response content
        soup = BeautifulSoup(current_response.text, 'html.parser')

        # Extract meta title
        meta_title = soup.title.string.strip() if soup.title else None
        if not meta_title:
            og_title = soup.find('meta', property='og:title')
            meta_title = og_title['content'].strip() if og_title else None

        # Extract meta description
        meta_description_tag = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_description_tag.get('content').strip() if meta_description_tag else None
        if not meta_description:
            og_description = soup.find('meta', property='og:description')
            meta_description = og_description['content'].strip() if og_description else None

        # Extract H1 tags
        h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]

        # Prepare the result
        result = {
            'url': url,
            'final_url': final_url,
            'initial_status_code': redirect_steps[0]['status_code'],
            'final_status_code': final_status_code,
            'response_time': response_time,
            'content_type': current_response.headers.get('Content-Type'),
            'redirect_steps': redirect_steps,
            'is_redirected': len(redirect_steps) > 1,  # More than 1 step means redirected
            'meta_title': meta_title,
            'meta_description': meta_description,
            'h1_tags': h1_tags,
        }

        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

def home(request):
    api_urls = {
        'Check URL Status': reverse('check_url_status'),
    }
    response_content = "<h1>Success! The server is running.</h1><ul>"
    for name, url in api_urls.items():
        response_content += f"<li><a href='{url}'>{name}</a></li>"
    response_content += "</ul>"
    return HttpResponse(response_content)
