#!/usr/bin/env node
/**
 * Simple Golden Wings Content Hunter
 * Just finds Golden Wings documentary files - nothing fancy
 */

const fs = require('fs').promises;
const path = require('path');

// Simple configuration - just the essentials
const CONFIG = {
    // Golden Wings keywords to search for
    keywords: [
        'golden wings', 'robyn stewart', 'robin stewart', 'jay ricks', 
        'henry stewart', 'caleb stewart', 'jock bethune', 'millie alford',
        'flight attendant', 'stewardess', 'american airlines', 'boeing 747',
        'documentary', 'film festival', 'recovery', 'sobriety', '9/11',
        'lgbtq', 'gay', 'coming out', 'grandfather', 'father', 'legacy'
    ],
    
    // File types to search
    extensions: ['.md', '.txt', '.json', '.docx', '.doc', '.pdf', '.csv', '.log', '.html'],
    
    // Directories to search (simple paths)
    searchDirs: [
        'E:\\',                    // Added: scan Google Drive (E:) root
        'D:\\Film Projects\\Golden Wings',
        'D:\\golden-wings-reconoganza', 
        'G:\\dev\\WhisperPS',
        'G:\\accelerate grocery',
        'D:\\YOUTUBE',
        'D:\\gdrive',
        'C:\\Users\\nobby\\Desktop',
        'C:\\Users\\nobby\\Documents'
    ]
};

class SimpleContentHunter {
    constructor() {
        this.results = [];
    }

    async hunt() {
        console.log('🎬 Simple Golden Wings Content Hunter');
        console.log('=====================================');
        
        for (const dir of CONFIG.searchDirs) {
            try {
                await fs.access(dir);
                console.log(`📁 Searching: ${dir}`);
                await this.searchDirectory(dir);
            } catch (error) {
                console.log(`⚠️  Skipping ${dir} (not accessible)`);
            }
        }
        
        // Sort by relevance score
        this.results.sort((a, b) => b.score - a.score);
        
        console.log(`\n✅ Found ${this.results.length} relevant files`);
        await this.generateReport();
    }

    async searchDirectory(dirPath, depth = 0) {
        if (depth > 5) return; // Go deeper to find more files
        
        try {
            const entries = await fs.readdir(dirPath, { withFileTypes: true });
            
            for (const entry of entries) {
                const fullPath = path.join(dirPath, entry.name);
                
                if (entry.isDirectory()) {
                    // Skip common junk directories and self-generated content
                    if (entry.name.includes('node_modules') || 
                        entry.name.includes('.git') || 
                        entry.name.includes('cache') ||
                        entry.name.includes('backup') ||
                        entry.name.includes('__pycache__') ||
                        entry.name.includes('venv') ||
                        entry.name.includes('Media Cache') ||
                        entry.name.includes('Auto-Save')) {
                        continue;
                    }
                    await this.searchDirectory(fullPath, depth + 1);
                } else if (entry.isFile()) {
                    // Skip self-generated files and obvious junk
                    if (this.shouldSkipFile(fullPath, entry.name)) {
                        continue;
                    }
                    await this.analyzeFile(fullPath);
                }
            }
        } catch (error) {
            // Skip directories we can't read
        }
    }

    shouldSkipFile(filePath, fileName) {
        const fileNameLower = fileName.toLowerCase();
        const pathLower = filePath.toLowerCase();
        
        // Skip self-generated content hunter files FIRST (before any includes)
        if (fileNameLower.includes('content-inventory') ||
            fileNameLower.includes('content-summary') ||
            fileNameLower.includes('top50') ||
            fileNameLower.includes('top100') ||
            fileNameLower.includes('top101') ||
            fileNameLower.includes('top201') ||
            fileName === 'TOP50.md' ||
            fileName === 'TOP100.md' ||
            fileName === 'TOP101-200.md' ||
            fileName === 'TOP201-300.md' ||
            fileName === 'content-inventory.csv' ||
            fileName === 'golden-wings-content-inventory-detailed.json' ||
            fileName === 'golden-wings-content-summary.json' ||
            fileName === 'CONTENT-SUMMARY.md' ||
            fileNameLower.includes('exodus_report') ||
            fileNameLower.includes('allfiles.csv')) {
            return true; // Always skip these, regardless of path
        }
        
        // ALWAYS INCLUDE Golden Wings specific content (overrides other exclusions)
        // But be more specific about file names, not just paths
        if (fileNameLower.includes('golden wings') ||
            fileNameLower.includes('caleb_stewart') ||
            fileNameLower.includes('robyn stewart') ||
            fileNameLower.includes('robin stewart') ||
            fileNameLower.includes('jay ricks') ||
            fileNameLower.includes('jock bethune') ||
            fileNameLower.includes('millie alford') ||
            fileNameLower.includes('henry stewart') ||
            fileNameLower.includes('lightscamerajourney') ||
            fileNameLower.includes('indiedocjourney') ||
            fileNameLower.includes('festival strategy') ||
            fileNameLower.includes('documentary analysis') ||
            fileNameLower.includes('press release') ||
            pathLower.includes('press kit') ||
            pathLower.includes('transcripts') ||
            pathLower.includes('laurels')) {
            return false; // Don't skip these
        }
        
        // Skip security/hacking content (false positives)
        if (pathLower.includes('blackhat-python') ||
            pathLower.includes('ethical hacking') ||
            pathLower.includes('penetration-testing') ||
            pathLower.includes('cybersecurity') ||
            pathLower.includes('hacking') ||
            pathLower.includes('exploit') ||
            pathLower.includes('breach')) {
            return true;
        }
        
        // Skip business/customer data (not documentary content)
        if (pathLower.includes('axonify') ||
            pathLower.includes('hubspot') ||
            pathLower.includes('accelerate_grocery') ||
            pathLower.includes('unfi-active-customers') ||
            fileNameLower.includes('customers.csv') ||
            fileNameLower.includes('grocery') ||
            fileNameLower.includes('peggy') ||
            fileNameLower.includes('accelerate') ||
            fileNameLower.includes('unfi') ||
            fileNameLower.includes('store-list') ||
            fileNameLower.includes('subscribers') ||
            fileNameLower.includes('billing-history') ||
            fileNameLower.includes('banners') ||
            fileNameLower.includes('owner') ||
            fileNameLower.includes('model-') ||
            fileNameLower.includes('sheet1-') ||
            fileNameLower.includes('sheet2-') ||
            fileNameLower.includes('region-pivot') ||
            fileNameLower.includes('final-model')) {
            return true;
        }
        
        // Skip system/browser data
        if (pathLower.includes('appdata/local') ||
            pathLower.includes('programdata') ||
            pathLower.includes('dnsfilters') ||
            pathLower.includes('cache') ||
            pathLower.includes('vivaldi') ||
            pathLower.includes('chrome') ||
            pathLower.includes('firefox')) {
            return true;
        }
        
        // Skip large data dumps
        if (fileNameLower.includes('subdomains.txt') ||
            fileNameLower.includes('dns_filter') ||
            fileNameLower.includes('domain-list') ||
            fileNameLower.includes('subdomain') ||
            fileNameLower.includes('data-dump')) {
            return true;
        }
        
        // Skip PowerShell transcripts (too many, low value)
        if (fileNameLower.includes('powershell_transcript')) {
            return true;
        }
        
        // Skip system/temp files
        if (fileNameLower.includes('thumbs.db') ||
            fileNameLower.includes('.ds_store') ||
            fileNameLower.includes('desktop.ini') ||
            fileNameLower.includes('.tmp') ||
            fileNameLower.includes('.temp') ||
            fileNameLower.includes('.bak') ||
            fileNameLower.includes('.backup') ||
            fileNameLower.includes('~$') ||
            fileName.startsWith('.')) {
            return true;
        }
        
        // Skip Adobe cache and temp files
        if (pathLower.includes('adobe premiere pro auto-save') ||
            pathLower.includes('media cache') ||
            pathLower.includes('analyzer cache') ||
            pathLower.includes('motion graphics template media')) {
            return true;
        }
        
        // Skip license/legal files
        if (fileNameLower.includes('eula') ||
            fileNameLower.includes('license') ||
            fileNameLower.includes('licence') ||
            fileNameLower.includes('terms of service') ||
            fileNameLower.includes('changelog') ||
            fileNameLower.includes('warranty')) {
            return true;
        }
        
        // Skip development/technical files
        if (fileNameLower.includes('package-lock.json') ||
            fileNameLower.includes('tsconfig.json') ||
            fileNameLower.includes('package.json') ||
            fileNameLower.includes('cypress.json') ||
            fileNameLower.includes('node_modules') ||
            fileNameLower.includes('app-') ||
            fileNameLower.includes('deadline') ||
            fileNameLower.includes('metasploit') ||
            fileNameLower.includes('nmap') ||
            fileNameLower.includes('scanning') ||
            fileNameLower.includes('penetration') ||
            fileNameLower.includes('exploit') ||
            fileNameLower.includes('payload') ||
            fileNameLower.includes('meterpreter') ||
            fileNameLower.includes('netcat') ||
            fileNameLower.includes('kali') ||
            fileNameLower.includes('ethical hacking') ||
            pathLower.includes('deadline') ||
            pathLower.includes('thinkbox')) {
            return true;
        }
        
        // Skip system logs and technical files
        if (fileNameLower.includes('powershell_') ||
            fileNameLower.includes('computerinfo_') ||
            fileNameLower.includes('drivers_') ||
            fileNameLower.includes('systeminfo_') ||
            fileNameLower.includes('system_errors_') ||
            fileNameLower.includes('wu_') ||
            fileNameLower.includes('speccy.txt') ||
            fileNameLower.includes('gpu_') ||
            fileNameLower.includes('.log') ||
            fileNameLower.includes('native-fireshot.log') ||
            fileNameLower.includes('plugin loading.log')) {
            return true;
        }
        
        // Skip generic web/HTML files that aren't Golden Wings specific
        if (fileNameLower.includes('saved_resource') ||
            fileNameLower.includes('index.html') ||
            fileNameLower.includes('search(') ||
            fileNameLower.includes('privacy') ||
            fileNameLower.includes('terms-of-use') ||
            fileNameLower.includes('accessibility') ||
            fileNameLower.includes('yelp') ||
            fileNameLower.includes('webhook') ||
            fileNameLower.includes('rss.html') ||
            fileNameLower.includes('static.html')) {
            return true;
        }
        
        // Skip Instagram/social media date-stamped files (not Golden Wings specific)
        if (fileNameLower.match(/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_utc\.txt$/)) {
            return true;
        }
        
        // Skip generic tutorial/course content
        if (fileNameLower.includes('exercise') ||
            fileNameLower.includes('tutorial') ||
            fileNameLower.includes('course overview') ||
            fileNameLower.includes('welcome challenge') ||
            pathLower.includes('ethical hacking') ||
            pathLower.includes('python')) {
            return true;
        }
        
        return false;
    }

    async analyzeFile(filePath) {
        const ext = path.extname(filePath).toLowerCase();
        const fileName = path.basename(filePath).toLowerCase();
        
        // Only check files we care about
        if (!CONFIG.extensions.includes(ext)) return;
        
        try {
            const stats = await fs.stat(filePath);
            
            // Skip huge files
            if (stats.size > 10 * 1024 * 1024) return; // 10MB limit
            
            let score = 0;
            let matchedKeywords = [];
            
            // Check filename for keywords
            for (const keyword of CONFIG.keywords) {
                if (fileName.includes(keyword.toLowerCase())) {
                    score += 5; // Filename matches are worth more
                    matchedKeywords.push(keyword);
                }
            }
            
            // Also check for partial matches and related terms
            const relatedTerms = [
                'caleb', 'stewart', 'robyn', 'robin', 'jay', 'henry', 'jock', 'millie',
                'flight', 'attendant', 'steward', 'airline', 'boeing', 'aircraft',
                'film', 'movie', 'documentary', 'festival', 'screening', 'premiere',
                'interview', 'transcript', 'voice', 'audio', 'video', 'footage'
            ];
            
            for (const term of relatedTerms) {
                if (fileName.includes(term.toLowerCase())) {
                    score += 1; // Partial matches get smaller score
                    if (!matchedKeywords.includes(term)) {
                        matchedKeywords.push(term);
                    }
                }
            }
            
            // Check file content for text files
            if (['.txt', '.md', '.json', '.csv', '.log', '.html'].includes(ext)) {
                try {
                    const content = await fs.readFile(filePath, 'utf8');
                    const contentLower = content.toLowerCase();
                    
                    // Check main keywords
                    for (const keyword of CONFIG.keywords) {
                        const matches = (contentLower.match(new RegExp(keyword.toLowerCase(), 'g')) || []).length;
                        if (matches > 0) {
                            score += matches;
                            if (!matchedKeywords.includes(keyword)) {
                                matchedKeywords.push(keyword);
                            }
                        }
                    }
                    
                    // Check related terms in content too
                    for (const term of relatedTerms) {
                        const matches = (contentLower.match(new RegExp(term.toLowerCase(), 'g')) || []).length;
                        if (matches > 0) {
                            score += Math.min(matches, 3); // Cap at 3 points per term
                            if (!matchedKeywords.includes(term)) {
                                matchedKeywords.push(term);
                            }
                        }
                    }
                } catch (error) {
                    // Can't read file content, just use filename score
                }
            }
            
            // Be more inclusive - save files with any relevance
            if (score > 0 || matchedKeywords.length > 0) {
                this.results.push({
                    path: filePath,
                    name: path.basename(filePath),
                    score: score,
                    keywords: matchedKeywords,
                    size: stats.size,
                    modified: stats.mtime,
                    extension: ext
                });
                
                console.log(`  📄 ${path.basename(filePath)} (Score: ${score})`);
            }
            
        } catch (error) {
            // Skip files we can't access
        }
    }

    async generateReport() {
        const top50 = this.results.slice(0, 50);
        
        let markdown = `# 🏆 Golden Wings Content - Top 50

**Generated:** ${new Date().toLocaleString()}
**Total Files:** ${this.results.length}

---

`;

        top50.forEach((file, index) => {
            const rank = index + 1;
            const scoreBar = '█'.repeat(Math.min(20, Math.floor(file.score / 2)));
            const sizeKB = (file.size / 1024).toFixed(1);
            
            markdown += `## ${rank}. ${file.name}

**Score:** ${file.score} ${scoreBar}
**Path:** \`${file.path}\`
**Size:** ${sizeKB} KB
**Modified:** ${file.modified.toLocaleDateString()}
**Keywords:** ${file.keywords.join(', ')}

---
`;
        });
        
        await fs.writeFile('TOP50.md', markdown);
        console.log('\n📊 Report saved to TOP50.md');
    }
}

// Run it
if (require.main === module) {
    const hunter = new SimpleContentHunter();
    hunter.hunt().catch(console.error);
}

module.exports = SimpleContentHunter;
