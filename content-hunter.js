const fs = require('fs').promises;
const path = require('path');

// Your documentary keywords - the holy grail search terms
const KEYWORDS = [
  // Core People
  'robyn stewart', 'robin stewart', 'jay ricks', 'henry stewart', 
  'caleb mills stewart', 'jock bethune', 'millie alford',
  
  // Project Names
  'golden wings', 'fifty year flight path', 'sassy mcgraw',
  
  // Aviation Terms
  'flight attendant', 'stewardess', 'american airlines', 'boeing 747',
  'aviation', 'airport', 'dfw', 'jfk', 'frankfurt', 'cr smith',
  
  // Themes & Events
  'recovery', 'sobriety', 'rehab', 'alcoholism', 'addiction',
  '9/11', 'september 11', 'terrorist', 'world trade center',
  'lgbtq', 'gay', 'coming out', 'sexuality', 'acceptance',
  
  // Production Terms
  'documentary', 'film festival', 'screening', 'premiere',
  'silicon beach', 'sundance', 'tribeca', 'amsterdam',
  'press release', 'marketing', 'distribution', 'trailer',
  
  // Business Terms
  'llc', 'ein', 'budget', 'timeline', 'deadline', 'contract',
  'festival submission', 'laurel', 'award', 'winner',
  
  // Emotional/Story Terms
  'grandfather', 'father', 'death', 'passed away', 'funeral',
  'letter', 'grief', 'legacy', 'generations', 'family',
  'eiffel tower', 'clair de lune', 'paparazzi', 'flashbulbs'
];

// File types to search
const SEARCH_EXTENSIONS = [
  '.md', '.txt', '.json', '.docx', '.doc', '.pdf', '.rtf',
  '.csv', '.log', '.notes', '.html', '.xml', '.yml', '.yaml',
  '.fountain', '.fdx', '.screenplay', '.final', '.draft'
];

class DocumentaryContentHunter {
  constructor() {
    this.results = [];
    this.searchPaths = [
      process.env.HOME + '/Documents',
      process.env.HOME + '/Desktop',
      process.env.HOME + '/Downloads',
      process.env.HOME + '/Movies',
      process.env.HOME + '/Pictures',
      // Add your specific project folders here
      // '/path/to/your/golden-wings-folder',
    ];
  }

  async searchDirectory(dirPath, maxDepth = 5, currentDepth = 0) {
    if (currentDepth >= maxDepth) return;
    
    try {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        
        // Skip system/hidden folders
        if (entry.name.startsWith('.') || 
            entry.name.includes('node_modules') ||
            entry.name.includes('Library') ||
            entry.name.includes('System')) {
          continue;
        }

        if (entry.isDirectory()) {
          await this.searchDirectory(fullPath, maxDepth, currentDepth + 1);
        } else if (entry.isFile()) {
          await this.analyzeFile(fullPath);
        }
      }
    } catch (error) {
      console.log(`Skipping ${dirPath}: ${error.message}`);
    }
  }

  async analyzeFile(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const fileName = path.basename(filePath).toLowerCase();
    
    // Check if it's a file type we care about
    if (!SEARCH_EXTENSIONS.includes(ext)) return;
    
    try {
      // Quick filename relevance check
      const filenameMatches = KEYWORDS.filter(keyword => 
        fileName.includes(keyword.toLowerCase())
      );

      // For text files, also check content
      let contentMatches = [];
      if (['.md', '.txt', '.json', '.html', '.xml'].includes(ext)) {
        const content = await fs.readFile(filePath, 'utf8');
        const contentLower = content.toLowerCase();
        
        contentMatches = KEYWORDS.filter(keyword => 
          contentLower.includes(keyword.toLowerCase())
        );
      }

      // Calculate relevance score
      const totalMatches = [...new Set([...filenameMatches, ...contentMatches])];
      const relevanceScore = totalMatches.length;

      if (relevanceScore > 0) {
        this.results.push({
          filePath,
          fileName: path.basename(filePath),
          extension: ext,
          relevanceScore,
          matchedKeywords: totalMatches,
          filenameMatches,
          contentMatches: contentMatches.slice(0, 10), // Limit for readability
          lastModified: (await fs.stat(filePath)).mtime,
          size: (await fs.stat(filePath)).size
        });

        console.log(`📄 Found: ${filePath} (Score: ${relevanceScore})`);
      }
    } catch (error) {
      // Silently skip files we can't read
    }
  }

  async generateReport() {
    // Sort by relevance score (highest first)
    this.results.sort((a, b) => b.relevanceScore - a.relevanceScore);

    const report = {
      searchDate: new Date().toISOString(),
      totalFilesFound: this.results.length,
      searchPaths: this.searchPaths,
      keywordsUsed: KEYWORDS,
      results: this.results
    };

    // Save detailed JSON report
    await fs.writeFile(
      'golden-wings-content-inventory.json', 
      JSON.stringify(report, null, 2)
    );

    // Create readable summary
    const summary = this.createSummaryReport();
    await fs.writeFile('CONTENT-SUMMARY.md', summary);

    console.log(`\n🎬 SEARCH COMPLETE!`);
    console.log(`📁 Found ${this.results.length} relevant files`);
    console.log(`📊 Results saved to: golden-wings-content-inventory.json`);
    console.log(`📝 Summary saved to: CONTENT-SUMMARY.md`);
  }

  createSummaryReport() {
    const topFiles = this.results.slice(0, 20);
    
    return `# Golden Wings Documentary - Content Inventory

**Search Date:** ${new Date().toLocaleString()}
**Total Files Found:** ${this.results.length}

## 🏆 TOP RELEVANCE FILES

${topFiles.map((file, i) => `
### ${i + 1}. ${file.fileName}
- **Path:** \`${file.filePath}\`
- **Relevance Score:** ${file.relevanceScore}
- **Keywords:** ${file.matchedKeywords.join(', ')}
- **Last Modified:** ${file.lastModified.toLocaleDateString()}
- **Size:** ${(file.size / 1024).toFixed(1)} KB
`).join('\n')}

## 📊 FILE TYPE BREAKDOWN

${this.getFileTypeBreakdown()}

## 🔍 KEYWORD FREQUENCY

${this.getKeywordFrequency()}

---
*Generated by Golden Wings Content Hunter 🛫*
`;
  }

  getFileTypeBreakdown() {
    const breakdown = {};
    this.results.forEach(file => {
      breakdown[file.extension] = (breakdown[file.extension] || 0) + 1;
    });
    
    return Object.entries(breakdown)
      .sort((a, b) => b[1] - a[1])
      .map(([ext, count]) => `- **${ext}**: ${count} files`)
      .join('\n');
  }

  getKeywordFrequency() {
    const freq = {};
    this.results.forEach(file => {
      file.matchedKeywords.forEach(keyword => {
        freq[keyword] = (freq[keyword] || 0) + 1;
      });
    });
    
    return Object.entries(freq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15)
      .map(([keyword, count]) => `- **${keyword}**: ${count} mentions`)
      .join('\n');
  }

  async hunt() {
    console.log('🔍 Starting Golden Wings content hunt...');
    console.log(`🎯 Searching for ${KEYWORDS.length} keywords`);
    console.log(`📁 Scanning ${this.searchPaths.length} directories`);
    
    for (const searchPath of this.searchPaths) {
      console.log(`\n📂 Searching: ${searchPath}`);
      await this.searchDirectory(searchPath);
    }
    
    await this.generateReport();
  }
}

// Run the hunt!
const hunter = new DocumentaryContentHunter();
hunter.hunt().catch(console.error);
