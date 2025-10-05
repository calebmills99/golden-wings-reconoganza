const fs = require('fs').promises;
const path = require('path');
const pLimit = require('p-limit');

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
    const homeDir = process.env.USERPROFILE || process.env.HOME;
    
    // Validate home directory exists
    if (!homeDir) {
      throw new Error('No home directory found. USERPROFILE and HOME environment variables are not set.');
    }
    
    this.searchPaths = [
      path.join(homeDir, 'Documents'),
      path.join(homeDir, 'Desktop'),
      path.join(homeDir, 'Downloads'),
      path.join(homeDir, 'Videos'),
      path.join(homeDir, 'Pictures'),
      // Add your specific project folders here
      // '/path/to/your/golden-wings-folder',
    ];
    
    // Throttling configuration - limit concurrent operations
    this.directoryLimit = pLimit(5);  // Max 5 concurrent directory scans
    this.fileLimit = pLimit(10);      // Max 10 concurrent file analyses
  }

  async searchDirectory(dirPath, maxDepth = 5, currentDepth = 0) {
    if (currentDepth >= maxDepth) return;
    
    try {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      
      // Create throttled tasks for processing entries
      const tasks = [];
      
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
          // Check for symlinks to prevent infinite recursion
          try {
            const realPath = await fs.realpath(fullPath);
            if (realPath !== fullPath) {
              console.log(`🔗 Skipping symlink: ${fullPath} -> ${realPath}`);
              continue;
            }
          } catch (symlinkError) {
            // If we can't resolve the symlink, skip it
            console.log(`🔗 Skipping unresolvable symlink: ${fullPath}`);
            continue;
          }
          // Add throttled directory search task
          tasks.push(this.directoryLimit(() => this.searchDirectory(fullPath, maxDepth, currentDepth + 1)));
        } else if (entry.isFile()) {
          // Add throttled file analysis task
          tasks.push(this.fileLimit(() => this.analyzeFile(fullPath)));
        }
      }
      
      // Wait for all throttled tasks to complete
      await Promise.all(tasks);
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
      // Quick filename relevance check (case-insensitive)
      const filenameMatches = KEYWORDS.filter(keyword => 
        fileName.includes(keyword.toLowerCase()) || 
        fileName.includes(keyword.toUpperCase()) ||
        fileName.includes(keyword.charAt(0).toUpperCase() + keyword.slice(1).toLowerCase())
      );

      // For text files, also check content
      let contentMatches = [];
      if (['.md', '.txt', '.json', '.html', '.xml'].includes(ext)) {
        try {
          // Check file size first to avoid memory issues
          const stats = await fs.stat(filePath);
          const maxFileSize = 10 * 1024 * 1024; // 10MB limit
          
          if (stats.size > maxFileSize) {
            console.log(`⚠️  Skipping large file ${filePath} (${(stats.size / 1024 / 1024).toFixed(1)}MB)`);
          } else {
            const content = await fs.readFile(filePath, 'utf8');
            const contentLower = content.toLowerCase();
            
            contentMatches = KEYWORDS.filter(keyword => 
              contentLower.includes(keyword.toLowerCase())
            );
          }
        } catch (readError) {
          // File might be locked or unreadable
          console.log(`⚠️  Could not read content of ${filePath}: ${readError.message}`);
        }
      }

      // Calculate relevance score
      const totalMatches = [...new Set([...filenameMatches, ...contentMatches])];
      const relevanceScore = totalMatches.length;

      if (relevanceScore > 0) {
        try {
          const stats = await fs.stat(filePath);
          this.results.push({
            filePath,
            fileName: path.basename(filePath),
            extension: ext,
            relevanceScore,
            matchedKeywords: totalMatches,
            filenameMatches,
            contentMatches: contentMatches.slice(0, 10), // Limit for readability
            lastModified: stats.mtime,
            size: stats.size
          });

          console.log(`📄 Found: ${filePath} (Score: ${relevanceScore})`);
        } catch (statError) {
          // File might have been deleted between content check and stat call
          console.log(`⚠️  File stats unavailable for ${filePath}: ${statError.message}`);
        }
      }
    } catch (error) {
      // Silently skip files we can't read
    }
  }

  async generateReport() {
    try {
      // Sort by relevance score (highest first)
      this.results.sort((a, b) => b.relevanceScore - a.relevanceScore);

      const report = {
        searchDate: new Date().toISOString(),
        totalFilesFound: this.results.length,
        searchPaths: this.searchPaths,
        keywordsUsed: KEYWORDS,
        results: this.results
      };

      // Save detailed JSON report with proper error handling
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
    } catch (error) {
      console.error(`❌ Error generating report: ${error.message}`);
      throw error;
    }
  }

  // Cleanup method for proper resource management
  cleanup() {
    // Clear results array to free memory
    this.results = [];
    console.log('🧹 Cleanup completed - memory freed');
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
    console.log(`⚡ Throttling enabled: 5 concurrent directory scans, 10 concurrent file analyses`);
    
    // Validate search paths before starting
    const validPaths = [];
    for (const searchPath of this.searchPaths) {
      try {
        await fs.access(searchPath);
        validPaths.push(searchPath);
      } catch (error) {
        console.log(`⚠️  Skipping non-existent path: ${searchPath}`);
      }
    }
    
    if (validPaths.length === 0) {
      console.log('❌ No valid search paths found. Please check your directory structure.');
      return;
    }
    
    // Process directories with throttling
    const searchTasks = validPaths.map(searchPath => 
      this.directoryLimit(async () => {
        console.log(`\n📂 Searching: ${searchPath}`);
        try {
          await this.searchDirectory(searchPath);
        } catch (error) {
          console.log(`❌ Error searching ${searchPath}: ${error.message}`);
          // Continue with other directories even if one fails
        }
      })
    );
    
    await Promise.all(searchTasks);
    
    await this.generateReport();
  }
}

// Run the hunt with proper cleanup
const hunter = new DocumentaryContentHunter();

// Handle process termination gracefully
process.on('SIGINT', () => {
  console.log('\n🛑 Process interrupted. Cleaning up...');
  hunter.cleanup();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Process terminated. Cleaning up...');
  hunter.cleanup();
  process.exit(0);
});

// Run the hunt with cleanup
hunter.hunt()
  .then(() => {
    hunter.cleanup();
  })
  .catch(error => {
    console.error('❌ Hunt failed:', error.message);
    hunter.cleanup();
    process.exit(1);
  });
