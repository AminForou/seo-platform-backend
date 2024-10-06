from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CSVFileSerializer
import csv
import io
from urllib.parse import urlparse, parse_qs

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