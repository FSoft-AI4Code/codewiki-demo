#!/usr/bin/env python3
"""
Automatically generate projects.json by scanning the docs directory
This makes the demo work automatically with new project documentation

Usage: python generate-projects.py
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path(__file__).parent / 'docs'
OUTPUT_FILE = Path(__file__).parent / 'projects.json'

# Language detection patterns
LANGUAGE_PATTERNS = {
    'Python': ['python', 'langflow', 'zulip', 'rasa', 'openhands', 'graphrag'],
    'JavaScript': ['javascript', 'svelte', 'chart.js', 'marktext', 'prettier', 'serverless'],
    'TypeScript': ['typescript', 'puppeteer', 'storybook', 'mermaid', 'vite', 'strapi'],
    'Java': ['java', 'starrocks', 'logstash', 'material-components-android', 'trino', 'rxjava'],
    'C#': ['ml-agents', 'fluentvalidation', 'git-credential-manager', 'masstransit', 'stackexchange'],
    'C++': ['cpp', 'c++', 'electron', 'x64dbg', 'json', 'grpc', 'clickhouse'],
    'C': ['qmk', 'firmware', 'systemd', 'sumatrapdf', 'libsql', 'wazuh', 'sdl'],
}


def detect_language(repo_name):
    """Detect programming language based on repository name."""
    lower_name = repo_name.lower()
    
    for lang, patterns in LANGUAGE_PATTERNS.items():
        if any(p in lower_name for p in patterns):
            return lang
    
    return 'Unknown'


def parse_repo_name(folder_name):
    """Parse owner and repository name from folder name.
    
    Format: owner--repo-docs
    """
    # Remove -docs suffix
    clean_name = folder_name.rstrip('-docs')
    if folder_name.endswith('-docs'):
        clean_name = folder_name[:-5]
    
    parts = clean_name.split('--')
    
    if len(parts) == 2:
        owner = parts[0]
        repo = parts[1]  # Keep original repo name for URLs
        # Replace hyphens with spaces and capitalize words for display
        name = ' '.join(word.capitalize() for word in repo.split('-'))
        return {
            'owner': owner,
            'name': name,
            'repo': repo,
            'github_url': f'https://github.com/{owner}/{repo}',
            'deepwiki_url': f'https://deepwiki.com/{owner}/{repo}'
        }
    
    return {
        'owner': 'Unknown',
        'name': clean_name,
        'repo': clean_name,
        'github_url': None,
        'deepwiki_url': None
    }

def scan_docs_directory():
    """Scan the docs directory and collect project information."""
    print('📂 Scanning docs directory...')
    
    if not DOCS_DIR.exists():
        print(f'❌ Error: docs directory not found at {DOCS_DIR}')
        print('💡 Please create a docs/ directory or create a symlink to your documentation folder:')
        print('   ln -s /path/to/CodeWiki/output/docs ./docs')
        sys.exit(1)
    
    projects = []
    
    for folder in sorted(os.listdir(DOCS_DIR)):
        folder_path = DOCS_DIR / folder
        
        if not folder_path.is_dir():
            continue
        
        # Check if it has required files
        metadata_path = folder_path / 'metadata.json'
        module_tree_path = folder_path / 'module_tree.json'
        overview_path = folder_path / 'overview.md'
        
        if not overview_path.exists():
            print(f'⚠️  Skipping {folder} - no overview.md found')
            continue
        
        repo_info = parse_repo_name(folder)
        owner = repo_info['owner']
        name = repo_info['name']
        language = detect_language(folder)
        
        project = {
            'folder': folder,
            'owner': owner,
            'name': name,
            'repo': repo_info['repo'],
            'language': language,
            'github_url': repo_info['github_url'],
            'deepwiki_url': repo_info['deepwiki_url'],
            'components': 0,
            'modules': 0,
            'depth': 0,
            'model': None
        }
        
        # Load metadata if available
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                if 'generation_info' in metadata:
                    project['model'] = metadata['generation_info'].get('main_model')
                
                if 'statistics' in metadata:
                    project['components'] = metadata['statistics'].get('total_components', 0)
                    project['depth'] = metadata['statistics'].get('max_depth', 0)
            except Exception as error:
                print(f'⚠️  Error reading metadata for {folder}: {error}')
        
        # Count modules from module_tree
        if module_tree_path.exists():
            try:
                with open(module_tree_path, 'r', encoding='utf-8') as f:
                    module_tree = json.load(f)
                project['modules'] = len(module_tree)
            except Exception as error:
                print(f'⚠️  Error reading module tree for {folder}: {error}')
        
        projects.append(project)
        print(f'✅ Added {owner}/{name} ({language})')
    
    # Sort by main_model ('claude-sonnet-4' first), then owner, then name
    projects.sort(key=lambda p: (
        0 if p.get('model') == 'claude-sonnet-4' else 1,
        p['owner'],
        p['name']
    ))
    
    return projects


def generate_projects_json():
    """Generate the projects.json file."""
    projects = scan_docs_directory()
    
    output = {
        'generated': datetime.utcnow().isoformat() + 'Z',
        'count': len(projects),
        'projects': projects
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print('\n' + '=' * 60)
    print(f'✨ Successfully generated {OUTPUT_FILE}')
    print(f'📊 Total projects: {len(projects)}')
    
    # Summary by language
    lang_counts = {}
    for p in projects:
        lang = p['language']
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    print('\n📚 Projects by language:')
    for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
        print(f'   {lang}: {count}')
    
    print('=' * 60 + '\n')


# Run the generator
if __name__ == '__main__':
    try:
        generate_projects_json()
    except Exception as error:
        print(f'❌ Error: {error}')
        sys.exit(1)

