#!/usr/bin/env node
/**
 * Automatically generate projects.json by scanning the docs directory
 * This makes the demo work automatically with new project documentation
 * 
 * Usage: node generate-projects.js
 */

const fs = require('fs');
const path = require('path');

const DOCS_DIR = path.join(__dirname, 'docs');
const OUTPUT_FILE = path.join(__dirname, 'projects.json');

// Language detection patterns
const LANGUAGE_PATTERNS = {
    'Python': ['py', 'python', 'langflow', 'zulip', 'rasa', 'openhands', 'graphrag'],
    'JavaScript': ['js', 'javascript', 'svelte', 'chart.js', 'marktext', 'prettier', 'serverless'],
    'TypeScript': ['ts', 'typescript', 'puppeteer', 'storybook', 'mermaid', 'vite', 'strapi'],
    'Java': ['java', 'starrocks', 'logstash', 'material-components-android', 'trino', 'rxjava'],
    'C#': ['ml-agents', 'fluentvalidation', 'git-credential-manager', 'masstransit', 'stackexchange'],
    'C++': ['cpp', 'c++', 'electron', 'x64dbg', 'json', 'grpc', 'clickhouse'],
    'C': ['qmk', 'firmware', 'systemd', 'sumatrapdf', 'libsql', 'wazuh', 'sdl'],
};

function detectLanguage(repoName) {
    const lowerName = repoName.toLowerCase();
    
    for (const [lang, patterns] of Object.entries(LANGUAGE_PATTERNS)) {
        if (patterns.some(p => lowerName.includes(p))) {
            return lang;
        }
    }
    
    return 'Unknown';
}

function parseRepoName(folderName) {
    // Format: owner--repo-docs
    const parts = folderName.replace(/-docs$/, '').split('--');
    if (parts.length === 2) {
        return {
            owner: parts[0],
            name: parts[1].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        };
    }
    return {
        owner: 'Unknown',
        name: folderName.replace(/-docs$/, '')
    };
}

function scanDocsDirectory() {
    console.log('📂 Scanning docs directory...');
    
    if (!fs.existsSync(DOCS_DIR)) {
        console.error(`❌ Error: docs directory not found at ${DOCS_DIR}`);
        console.log('💡 Please create a docs/ directory or create a symlink to your documentation folder:');
        console.log('   ln -s /path/to/CodeWiki/output/docs ./docs');
        process.exit(1);
    }
    
    const projects = [];
    const folders = fs.readdirSync(DOCS_DIR);
    
    for (const folder of folders) {
        const folderPath = path.join(DOCS_DIR, folder);
        const stat = fs.statSync(folderPath);
        
        if (!stat.isDirectory()) continue;
        
        // Check if it has required files
        const metadataPath = path.join(folderPath, 'metadata.json');
        const moduleTreePath = path.join(folderPath, 'module_tree.json');
        const overviewPath = path.join(folderPath, 'overview.md');
        
        if (!fs.existsSync(overviewPath)) {
            console.log(`⚠️  Skipping ${folder} - no overview.md found`);
            continue;
        }
        
        const { owner, name } = parseRepoName(folder);
        const language = detectLanguage(folder);
        
        const project = {
            folder: folder,
            owner: owner,
            name: name,
            language: language,
            components: 0,
            modules: 0,
            depth: 0,
            model: null
        };
        
        // Load metadata if available
        if (fs.existsSync(metadataPath)) {
            try {
                const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
                
                if (metadata.generation_info) {
                    project.model = metadata.generation_info.main_model || null;
                }
                
                if (metadata.statistics) {
                    project.components = metadata.statistics.total_components || 0;
                    project.depth = metadata.statistics.max_depth || 0;
                }
            } catch (error) {
                console.warn(`⚠️  Error reading metadata for ${folder}:`, error.message);
            }
        }
        
        // Count modules from module_tree
        if (fs.existsSync(moduleTreePath)) {
            try {
                const moduleTree = JSON.parse(fs.readFileSync(moduleTreePath, 'utf8'));
                project.modules = Object.keys(moduleTree).length;
            } catch (error) {
                console.warn(`⚠️  Error reading module tree for ${folder}:`, error.message);
            }
        }
        
        projects.push(project);
        console.log(`✅ Added ${owner}/${name} (${language})`);
    }
    
    // Sort by owner, then name
    projects.sort((a, b) => {
        const ownerCompare = a.owner.localeCompare(b.owner);
        if (ownerCompare !== 0) return ownerCompare;
        return a.name.localeCompare(b.name);
    });
    
    return projects;
}

function generateProjectsJson() {
    const projects = scanDocsDirectory();
    
    const output = {
        generated: new Date().toISOString(),
        count: projects.length,
        projects: projects
    };
    
    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
    
    console.log('\n' + '='.repeat(60));
    console.log(`✨ Successfully generated ${OUTPUT_FILE}`);
    console.log(`📊 Total projects: ${projects.length}`);
    
    // Summary by language
    const langCounts = {};
    projects.forEach(p => {
        langCounts[p.language] = (langCounts[p.language] || 0) + 1;
    });
    
    console.log('\n📚 Projects by language:');
    Object.entries(langCounts)
        .sort((a, b) => b[1] - a[1])
        .forEach(([lang, count]) => {
            console.log(`   ${lang}: ${count}`);
        });
    
    console.log('='.repeat(60) + '\n');
}

// Run the generator
try {
    generateProjectsJson();
} catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
}
