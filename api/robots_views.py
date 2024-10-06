# api/robots_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    RobotsTxtInputSerializer,
    RobotsTxtComparisonSerializer,
    TestURLSerializer,
    MultiRobotsTestSerializer
)
import requests
import re
from difflib import unified_diff
from urllib.parse import urlparse
from robotexclusionrulesparser import RobotExclusionRulesParser

class RobotsTxtAnalyzerView(APIView):
    def post(self, request):
        serializer = RobotsTxtInputSerializer(data=request.data)
        if serializer.is_valid():
            url = serializer.validated_data.get('url')
            content = serializer.validated_data.get('content')

            if url:
                try:
                    response = requests.get(url)
                    fetch_status = response.status_code
                    robots_content = response.text

                    if response.status_code != 200:
                        return Response({
                            'fetch_status': fetch_status,
                            'error': f"Failed to fetch robots.txt. HTTP Status Code: {fetch_status}",
                            'robots_content': robots_content
                        }, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                robots_content = content
                fetch_status = None

            # Check if robots_content is valid robots.txt
            if not self.is_valid_robots_txt(robots_content):
                return Response({
                    'error': 'Invalid robots.txt content. It might be an HTML page or malformed content.',
                    'robots_content': robots_content
                }, status=status.HTTP_200_OK)

            # Syntax validation
            errors = self.validate_syntax(robots_content)

            # Parse robots.txt
            parsed_data = self.parse_robots_txt(robots_content)

            data = {
                'fetch_status': fetch_status,
                'errors': errors,
                'parsed_data': parsed_data,
                'robots_content': robots_content,
            }

            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def is_valid_robots_txt(self, content):
        # Simple check to see if content starts with a valid directive or comment
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if re.match(r'^(User-agent|Disallow|Allow|Sitemap|Crawl-delay):', line, re.I):
                return True
            else:
                return False
        return False

    def validate_syntax(self, content):
        errors = []
        lines = content.split('\n')
        directive_pattern = re.compile(
            r'^(User-agent|Disallow|Allow|Sitemap|Crawl-delay):', re.I)
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue  # Skip empty lines and comments
            if not directive_pattern.match(line):
                errors.append(f"Line {idx+1}: Unrecognized directive '{line}'")
        return errors

    def parse_robots_txt(self, content):
        lines = content.split('\n')
        agents = []
        current_agents = []
        current_rules = []
        sitemaps = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.lower().startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                if current_agents and current_rules:
                    # We have agents and rules collected, store them
                    agents.append({
                        'user_agent': current_agents.copy(),
                        'rules': current_rules.copy(),
                        'rule_count': len(current_rules)
                    })
                    current_agents = [agent]
                    current_rules.clear()
                else:
                    # Accumulate agents
                    current_agents.append(agent)
            elif line.lower().startswith('disallow:') or line.lower().startswith('allow:'):
                allowance = line.lower().startswith('allow:')
                path = line.split(':', 1)[1].strip()
                current_rules.append({
                    'path': path,
                    'allowance': allowance
                })
            elif line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                try:
                    sitemap_response = requests.head(sitemap_url)
                    sitemap_status = sitemap_response.status_code
                except Exception as e:
                    sitemap_status = 'Error'
                sitemaps.append({'url': sitemap_url, 'status': sitemap_status})
            else:
                # Unknown directive
                pass
        # After loop, store any remaining agents
        if current_agents:
            agents.append({
                'user_agent': current_agents.copy(),
                'rules': current_rules.copy(),
                'rule_count': len(current_rules)
            })
        # Compute stats
        total_user_agents = len(agents)
        total_rules = sum(agent['rule_count'] for agent in agents)
        disallow_rules = []
        allow_rules = []
        for agent in agents:
            for rule in agent['rules']:
                if rule['allowance']:
                    allow_rules.append(rule['path'])
                else:
                    disallow_rules.append(rule['path'])
        total_disallow_rules = len(disallow_rules)
        total_allow_rules = len(allow_rules)
        unique_disallow_rules = len(set(disallow_rules))
        unique_allow_rules = len(set(allow_rules))
        stats = {
            'total_user_agents': total_user_agents,
            'total_rules': total_rules,
            'total_disallow_rules': total_disallow_rules,
            'unique_disallow_rules': unique_disallow_rules,
            'total_allow_rules': total_allow_rules,
            'unique_allow_rules': unique_allow_rules,
        }
        return {'agents': agents, 'sitemaps': sitemaps, 'stats': stats}

class RobotsTxtComparisonView(APIView):
    def post(self, request):
        serializer = RobotsTxtComparisonSerializer(data=request.data)
        if serializer.is_valid():
            content1 = serializer.validated_data.get('content1')
            content2 = serializer.validated_data.get('content2')

            diff = list(unified_diff(
                content1.splitlines(),
                content2.splitlines(),
                fromfile='Version 1',
                tofile='Version 2',
                lineterm=''
            ))

            return Response({'diff': diff}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TestURLAgainstRobotsView(APIView):
    def post(self, request):
        serializer = TestURLSerializer(data=request.data)
        if serializer.is_valid():
            robots_url = serializer.validated_data.get('robots_url')
            robots_content = serializer.validated_data.get('robots_content')
            test_urls = serializer.validated_data.get('test_urls')
            user_agents = serializer.validated_data.get('user_agents') or ['*']

            if robots_url:
                try:
                    response = requests.get(robots_url)
                    robots_content = response.text
                except Exception as e:
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if not robots_content:
                return Response({'error': 'No robots.txt content provided.'}, status=status.HTTP_400_BAD_REQUEST)

            parser = RobotExclusionRulesParser()
            parser.parse(robots_content)

            results = []
            for url in test_urls:
                url_result = {'url': url, 'results': {}}
                for agent in user_agents:
                    allowed = parser.is_allowed(agent, url)
                    url_result['results'][agent] = allowed
                results.append(url_result)

            return Response({'results': results}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MultiRobotsTestView(APIView):
    def post(self, request):
        serializer = MultiRobotsTestSerializer(data=request.data)
        if serializer.is_valid():
            robots_contents = serializer.validated_data.get('robots_contents')
            test_urls = serializer.validated_data.get('test_urls')
            user_agents = serializer.validated_data.get('user_agents') or ['*']

            parsers = []
            for content in robots_contents:
                parser = RobotExclusionRulesParser()
                parser.parse(content)
                parsers.append(parser)

            results = []
            for url in test_urls:
                url_result = {'url': url, 'robots_results': []}
                for idx, parser in enumerate(parsers):
                    agents_result = {}
                    for agent in user_agents:
                        allowed = parser.is_allowed(agent, url)
                        agents_result[agent] = allowed
                    url_result['robots_results'].append({
                        'robots_index': idx,
                        'results': agents_result
                    })
                results.append(url_result)

            return Response({'results': results}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)