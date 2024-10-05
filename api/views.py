from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.urls import reverse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ContactMessageSerializer
from django.core.mail import send_mail
from django.conf import settings
import logging

from .serializers import CSVFileSerializer
import csv
import io
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

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
    


class ProcessCSVView(APIView):
    def post(self, request, format=None):
        serializer = CSVFileSerializer(data=request.data)
        if serializer.is_valid():
            csv_file = serializer.validated_data['file']
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)
                urls = []
                indexability_data = []
                for row in reader:
                    if row:
                        url = row[0]
                        urls.append(url)
                        if len(row) > 1 and row[1] != '':
                            indexability_data.append(row[1].lower() == 'true')
                        else:
                            indexability_data.append(None)  # No indexability data
                processed_data = self.process_urls(urls, indexability_data)
                return Response(processed_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def process_urls(self, urls, indexability_data):
        folder_structure = {}
        global_params = {}
        second_level_folders = {}  # New variable to store second-level folders

        indexability_data_provided = any(i is not None for i in indexability_data)

        for index, url in enumerate(urls):
            try:
                parsed_url = urlparse(url)
                path_segments = parsed_url.path.strip('/').split('/')
                is_indexable = indexability_data[index] if indexability_data[index] is not None else True

                level1 = path_segments[0] if len(path_segments) > 0 else 'root'
                level2 = path_segments[1] if len(path_segments) > 1 else 'root'
                level3 = path_segments[2] if len(path_segments) > 2 else 'root'

                # First-level folder processing
                folder = folder_structure.setdefault(level1, {
                    'count': 0,
                    'subfolders': {},
                    'params': {},
                    'paramSamples': {},
                    'sampleUrl': '',
                })
                folder['count'] += 1
                folder['sampleUrl'] = folder['sampleUrl'] or url

                if indexability_data_provided:
                    folder.setdefault('nonIndexableCount', 0)
                    if not is_indexable:
                        folder['nonIndexableCount'] += 1

                # Second-level folder processing within folder_structure
                subfolder = folder['subfolders'].setdefault(level2, {
                    'count': 0,
                    'subfolders': {},
                    'params': {},
                    'paramSamples': {},
                    'sampleUrl': '',
                })
                subfolder['count'] += 1
                subfolder['sampleUrl'] = subfolder['sampleUrl'] or url

                if indexability_data_provided:
                    subfolder.setdefault('nonIndexableCount', 0)
                    if not is_indexable:
                        subfolder['nonIndexableCount'] += 1

                # Third-level folder processing
                subsubfolder = subfolder['subfolders'].setdefault(level3, {
                    'count': 0,
                    'params': {},
                    'paramSamples': {},
                    'sampleUrl': '',
                })
                subsubfolder['count'] += 1
                subsubfolder['sampleUrl'] = subsubfolder['sampleUrl'] or url

                if indexability_data_provided:
                    subsubfolder.setdefault('nonIndexableCount', 0)
                    if not is_indexable:
                        subsubfolder['nonIndexableCount'] += 1

                # Parse query parameters
                query_params = parse_qs(parsed_url.query)
                for key, values in query_params.items():
                    # Global params
                    global_param = global_params.setdefault(key, {'count': 0, 'folders': {}})
                    global_param['count'] += len(values)
                    folder_data = global_param['folders'].setdefault(level1, {'count': 0, 'sampleUrl': url})
                    folder_data['count'] += len(values)

                    # Folder-specific params
                    folder['params'][key] = folder['params'].get(key, 0) + len(values)
                    folder['paramSamples'][key] = folder['paramSamples'].get(key, url)

                # **New**: Populate `second_level_folders`
                second_level_key = level2
                second_level_folder = second_level_folders.setdefault(second_level_key, {
                    'count': 0,
                    'subfolders': {},
                    'sampleUrl': '',
                })
                second_level_folder['count'] += 1
                second_level_folder['sampleUrl'] = second_level_folder['sampleUrl'] or url

                if indexability_data_provided:
                    second_level_folder.setdefault('nonIndexableCount', 0)
                    if not is_indexable:
                        second_level_folder['nonIndexableCount'] += 1

                # Add third-level subfolders under second-level folder
                third_level_key = level3
                third_level_folder = second_level_folder['subfolders'].setdefault(third_level_key, {
                    'count': 0,
                    'sampleUrl': '',
                })
                third_level_folder['count'] += 1
                third_level_folder['sampleUrl'] = third_level_folder['sampleUrl'] or url

            except Exception as e:
                print('Error processing URL:', url, e)
                continue

        return {
            'folderStructure': folder_structure,
            'secondLevelFolders': second_level_folders,
            'globalParams': global_params,
            'indexabilityDataProvided': indexability_data_provided,
        }