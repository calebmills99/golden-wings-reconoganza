# Create a fixed version with better Windows volume detection
fixed_script = '''const fs = require('fs').promises;
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

// Enhanced configuration with external config support
let CONFIG = {
    // Documentary keywords - the holy grail search terms
    KEYWORDS: [
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
    ],
    
    // Enhanced file type support
    SEARCH_EXTENSIONS: [
        // Text documents
        '.md', '.txt', '.json', '.docx', '.doc', '.pdf', '.rtf',
        '.csv', '.log', '.notes', '.html', '.xml', '.yml', '.yaml',
        '.fountain', '.fdx', '.screenplay', '.final', '.draft',
        
        // Media files (for metadata extraction)
        '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
        '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
        
        // Archive files
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
        
        // Project files
        '.prproj', '.fcpxml', '.aep', '.psd', '.ai'
    ],
    
    // Performance settings
    MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB limit
    MAX_DEPTH: 8, // Increased depth for thorough search
    WORKER_THREADS: Math.min(os.cpus().length, 4), // Use CPU cores efficiently
    BATCH_SIZE: 100, // Process files in batches
    
    // Search behavior
    SKIP_PATTERNS: [
        'node_modules', 'Library', 'System', 'Windows', 'Program Files',
        '.git', '.svn', '.DS_Store', 'Thumbs.db', '$Recycle.Bin',
        'quivr_parsed_data', 'powershell-configure-script',
        'System Volume Information', 'pagefile.sys', 'hiberfil.sys'
    ],
    
    // Backup and temporary folder patterns
    BACKUP_PATTERNS: [
        'backup', 'backups', 'time machine', 'snapshots', 'versions',
        '.Trashes', 'Recycler', 'RECYCLER', 'temp', 'tmp', 'cache'
    ],
    
    // Output settings
    REPORTS: {
        JSON_DETAILED: 'golden-wings-content-inventory-detailed.json',
        JSON_SUMMARY: 'golden-wings-content-summary.json',
        MARKDOWN: 'CONTENT-SUMMARY.md',
        CSV_EXPORT: 'content-inventory.csv'
    }
};

// Volume detection utilities
class VolumeDetector {
    static async getAllVolumes() {
        const platform = os.platform();
        let volumes = [];
        
        try {
            switch (platform) {
                case 'win32':
                    volumes = await this.getWindowsVolumes();
                    break;
                case 'darwin':
                    volumes = await this.getMacVolumes();
                    break;
                case 'linux':
                    volumes = await this.getLinuxVolumes();
                    break;
                default:
                    console.log(`⚠️  Platform ${platform} not specifically supported, using home directory`);
                    volumes = [os.homedir()];
            }
        } catch (error) {
            console.log(`⚠️  Error detecting volumes: ${error.message}, falling back to common directories`);
            volumes = await this.getFallbackDirectories();
        }
        
        return volumes;
    }
    
    static async getWindowsVolumes() {
        let volumes = [];
        
        try {
            // Method 1: Try PowerShell (more reliable than wmic)
            try {
                const result = execSync('powershell "Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID | ForEach-Object { $_.DeviceID }"', { 
                    encoding: 'utf8',
                    timeout: 10000 
                });
                const drives = result.split('\\r\\n').filter(line => line.trim().match(/^[A-Z]:$/));
                volumes = drives.map(drive => drive.trim() + '\\\\');
                console.log(`📀 PowerShell detected drives: ${drives.join(', ')}`);
            } catch (psError) {
                console.log('⚠️  PowerShell method failed, trying alternative...');
                
                // Method 2: Manual drive letter checking
                const possibleDrives = ['A:', 'B:', 'C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:', 'Q:', 'R:', 'S:', 'T:', 'U:', 'V:', 'W:', 'X:', 'Y:', 'Z:'];
                
                for (const drive of possibleDrives) {
                    try {
                        const drivePath = drive + '\\\\';
                        await fs.access(drivePath);
                        const stats = await fs.stat(drivePath);
                        if (stats.isDirectory()) {
                            volumes.push(drivePath);
                            console.log(`✅ Found accessible drive: ${drive}`);
                        }
                    } catch (error) {
                        // Drive not accessible, skip silently
                    }
                }
            }
            
            // If no volumes found, add common defaults
            if (volumes.length === 0) {
                const defaultDrives = ['C:\\\\', 'D:\\\\'];
                for (const drive of defaultDrives) {
                    try {
                        await fs.access(drive);
                        volumes.push(drive);
                        console.log(`✅ Added default drive: ${drive}`);
                    } catch (error) {
                        // Skip inaccessible default drives
                    }
                }
            }
            
        } catch (error) {
            console.log(`⚠️  Windows volume detection failed: ${error.message}`);
            volumes = ['C:\\\\'];
        }
        
        return volumes;
    }
    
    static async getMacVolumes() {
        try {
            const volumes = ['/'];
            
            // Check /Volumes for mounted drives
            try {
                const volumeEntries = await fs.readdir('/Volumes');
                volumeEntries.forEach(volume => {
                    volumes.push(path.join('/Volumes', volume));
                });
            } catch (error) {
                console.log('⚠️  Could not read /Volumes directory');
            }
            
            return volumes;
        } catch (error) {
            return ['/'];
        }
    }
    
    static async getLinuxVolumes() {
        try {
            const volumes = ['/'];
            
            // Check common mount points
            const mountPoints = ['/mnt', '/media', '/run/media'];
            
            for (const mountPoint of mountPoints) {
                try {
                    const entries = await fs.readdir(mountPoint);
                    entries.forEach(entry => {
                        volumes.push(path.join(mountPoint, entry));
                    });
                } catch (error) {
                    // Mount point doesn't exist or not accessible
                }
            }
            
            return volumes;
        } catch (error) {
            return ['/'];
        }
    }
    
    static async getFallbackDirectories() {
        // Fallback to user directories if volume detection completely fails
        const fallbackPaths = [
            os.homedir(),
            path.join(os.homedir(), 'Documents'),
            path.join(os.homedir(), 'Desktop'),
            path.join(os.homedir(), 'Downloads'),
            path.join(os.homedir(), 'Videos'),
            path.join(os.homedir(), 'Pictures')
        ];
        
        const accessiblePaths = [];
        for (const dirPath of fallbackPaths) {
            try {
                await fs.access(dirPath);
                const stats = await fs.stat(dirPath);
                if (stats.isDirectory()) {
                    accessiblePaths.push(dirPath);
                }
            } catch (error) {
                // Skip inaccessible paths
            }
        }
        
        console.log(`📁 Using fallback directories: ${accessiblePaths.length} found`);
        return accessiblePaths;
    }
}

// Progress tracking utility
class ProgressTracker {
    constructor() {
        this.startTime = Date.now();
        this.processedFiles = 0;
        this.foundFiles = 0;
        this.currentPath = '';
        this.totalEstimate = 0;
        this.lastUpdate = 0;
    }
    
    updateProgress(processedFiles, foundFiles, currentPath, totalEstimate = 0) {
        this.processedFiles = processedFiles;
        this.foundFiles = foundFiles;
        this.currentPath = currentPath;
        this.totalEstimate = totalEstimate;
        
        // Throttle updates to avoid spam
        const now = Date.now();
        if (now - this.lastUpdate > 2000) { // Update every 2 seconds
            this.displayProgress();
            this.lastUpdate = now;
        }
    }
    
    displayProgress() {
        const elapsed = (Date.now() - this.startTime) / 1000;
        const rate = this.processedFiles / elapsed;
        const eta = this.totalEstimate > 0 ? 
            Math.round((this.totalEstimate - this.processedFiles) / rate) : '?';
        
        console.log(`\\n📊 Progress: ${this.processedFiles} files processed | ${this.foundFiles} matches found`);
        console.log(`⏱️  Rate: ${rate.toFixed(1)} files/sec | ETA: ${eta}s`);
        console.log(`📁 Current: ...${this.currentPath.slice(-60)}`);
    }
    
    getFinalStats() {
        const totalTime = (Date.now() - this.startTime) / 1000;
        return {
            totalTime: totalTime.toFixed(1),
            averageRate: (this.processedFiles / totalTime).toFixed(1),
            processedFiles: this.processedFiles,
            foundFiles: this.foundFiles
        };
    }
}

// Enhanced DocumentaryContentHunter class
class DocumentaryContentHunter {
    constructor(configPath = null) {
        this.results = [];
        this.duplicates = new Map();
        this.volumeStats = new Map();
        this.progress = new ProgressTracker();
        this.processedPaths = new Set(); // Prevent duplicate processing
        
        // Load external config if provided
        if (configPath) {
            this.loadConfig(configPath);
        }
    }
    
    async loadConfig(configPath) {
        try {
            const configData = await fs.readFile(configPath, 'utf8');
            const externalConfig = JSON.parse(configData);
            CONFIG = { ...CONFIG, ...externalConfig };
            console.log(`📋 Loaded configuration from ${configPath}`);
        } catch (error) {
            console.log(`⚠️  Could not load config from ${configPath}, using defaults`);
        }
    }
    
    async getAllVolumes() {
        console.log('🔍 Detecting all available volumes...');
        const volumes = await VolumeDetector.getAllVolumes();
        
        // Filter out inaccessible volumes
        const accessibleVolumes = [];
        for (const volume of volumes) {
            try {
                await fs.access(volume);
                const stats = await fs.stat(volume);
                if (stats.isDirectory()) {
                    accessibleVolumes.push(volume);
                    console.log(`✅ Found accessible volume: ${volume}`);
                }
            } catch (error) {
                console.log(`❌ Volume not accessible: ${volume}`);
            }
        }
        
        return accessibleVolumes;
    }
    
    async searchAllVolumes() {
        const volumes = await this.getAllVolumes();
        console.log(`\\n🎯 Starting comprehensive search across ${volumes.length} volumes`);
        
        if (volumes.length === 0) {
            console.log('⚠️  No accessible volumes found! Check permissions or try running as administrator.');
            return;
        }
        
        // Process volumes in parallel with limited concurrency
        const concurrency = Math.min(volumes.length, 3); // Max 3 volumes at once
        const promises = [];
        
        for (let i = 0; i < volumes.length; i += concurrency) {
            const batch = volumes.slice(i, i + concurrency);
            const batchPromises = batch.map(volume => this.searchVolume(volume));
            promises.push(...batchPromises);
            
            // Wait for batch completion before starting next
            if (promises.length >= concurrency) {
                await Promise.all(promises.splice(0, concurrency));
            }
        }
        
        // Wait for any remaining promises
        if (promises.length > 0) {
            await Promise.all(promises);
        }
    }
    
    async searchVolume(volumePath) {
        console.log(`\\n💾 Searching volume: ${volumePath}`);
        
        try {
            const volumeStats = {
                path: volumePath,
                filesProcessed: 0,
                filesFound: 0,
                startTime: Date.now()
            };
            
            await this.searchDirectory(volumePath, CONFIG.MAX_DEPTH, 0, volumeStats);
            
            volumeStats.endTime = Date.now();
            volumeStats.duration = volumeStats.endTime - volumeStats.startTime;
            this.volumeStats.set(volumePath, volumeStats);
            
            console.log(`\\n✅ Completed ${volumePath}: ${volumeStats.filesFound} files found`);
        } catch (error) {
            console.log(`❌ Error searching volume ${volumePath}: ${error.message}`);
        }
    }
    
    async searchDirectory(dirPath, maxDepth = CONFIG.MAX_DEPTH, currentDepth = 0, volumeStats = null) {
        if (currentDepth >= maxDepth) return;
        
        // Prevent processing the same path twice
        const normalizedPath = path.resolve(dirPath);
        if (this.processedPaths.has(normalizedPath)) {
            return;
        }
        this.processedPaths.add(normalizedPath);
        
        try {
            const entries = await fs.readdir(dirPath, { withFileTypes: true });
            
            // Filter out unwanted directories early
            const filteredEntries = entries.filter(entry => {
                const entryPath = path.join(dirPath, entry.name);
                return !this.shouldSkipPath(entryPath, entry.name);
            });
            
            // Process entries in batches for better performance
            for (let i = 0; i < filteredEntries.length; i += CONFIG.BATCH_SIZE) {
                const batch = filteredEntries.slice(i, i + CONFIG.BATCH_SIZE);
                
                await Promise.all(batch.map(async (entry) => {
                    const fullPath = path.join(dirPath, entry.name);
                    
                    if (volumeStats) {
                        volumeStats.filesProcessed++;
                        this.progress.updateProgress(
                            volumeStats.filesProcessed, 
                            volumeStats.filesFound, 
                            fullPath
                        );
                    }
                    
                    if (entry.isDirectory()) {
                        await this.searchDirectory(fullPath, maxDepth, currentDepth + 1, volumeStats);
                    } else if (entry.isFile()) {
                        const result = await this.analyzeFile(fullPath);
                        if (result && volumeStats) {
                            volumeStats.filesFound++;
                        }
                    }
                }));
            }
            
        } catch (error) {
            console.log(`⚠️  Skipping ${dirPath}: ${error.message}`);
        }
    }
    
    shouldSkipPath(fullPath, entryName) {
        // Check skip patterns
        const pathLower = fullPath.toLowerCase();
        const nameLower = entryName.toLowerCase();
        
        // Skip hidden files and system folders
        if (entryName.startsWith('.') && entryName !== '.') return true;
        
        // Skip known system and unwanted folders
        for (const pattern of CONFIG.SKIP_PATTERNS) {
            if (pathLower.includes(pattern.toLowerCase()) || 
                nameLower.includes(pattern.toLowerCase())) {
                return true;
            }
        }
        
        // Skip backup folders (but log them for reference)
        for (const pattern of CONFIG.BACKUP_PATTERNS) {
            if (pathLower.includes(pattern.toLowerCase())) {
                console.log(`📦 Skipping backup folder: ${fullPath}`);
                return true;
            }
        }
        
        return false;
    }
    
    async analyzeFile(filePath) {
        const ext = path.extname(filePath).toLowerCase();
        const fileName = path.basename(filePath).toLowerCase();
        
        // Check if it's a file type we care about
        if (!CONFIG.SEARCH_EXTENSIONS.includes(ext)) return null;
        
        try {
            // Quick filename relevance check (case-insensitive)
            const filenameMatches = CONFIG.KEYWORDS.filter(keyword =>
                fileName.includes(keyword.toLowerCase()) ||
                fileName.includes(keyword.toUpperCase()) ||
                fileName.includes(keyword.charAt(0).toUpperCase() + keyword.slice(1).toLowerCase())
            );
            
            // For text files, also check content
            let contentMatches = [];
            const textExtensions = ['.md', '.txt', '.json', '.html', '.xml', '.csv', '.log'];
            
            if (textExtensions.includes(ext)) {
                try {
                    const stats = await fs.stat(filePath);
                    
                    if (stats.size <= CONFIG.MAX_FILE_SIZE) {
                        const content = await fs.readFile(filePath, 'utf8');
                        const contentLower = content.toLowerCase();
                        
                        contentMatches = CONFIG.KEYWORDS.filter(keyword =>
                            contentLower.includes(keyword.toLowerCase())
                        );
                    } else {
                        console.log(`⚠️  Skipping large file ${filePath} (${(stats.size / 1024 / 1024).toFixed(1)}MB)`);
                    }
                } catch (readError) {
                    console.log(`⚠️  Could not read content of ${filePath}: ${readError.message}`);
                }
            }
            
            // Calculate relevance score
            const totalMatches = [...new Set([...filenameMatches, ...contentMatches])];
            const relevanceScore = totalMatches.length;
            
            if (relevanceScore > 0) {
                try {
                    const stats = await fs.stat(filePath);
                    const fileHash = await this.getFileHash(filePath, stats.size);
                    
                    const result = {
                        filePath,
                        fileName: path.basename(filePath),
                        directory: path.dirname(filePath),
                        extension: ext,
                        relevanceScore,
                        matchedKeywords: totalMatches,
                        filenameMatches,
                        contentMatches: contentMatches.slice(0, 10), // Limit for readability
                        lastModified: stats.mtime,
                        created: stats.birthtime || stats.ctime,
                        size: stats.size,
                        fileHash,
                        volumePath: this.getVolumePath(filePath)
                    };
                    
                    // Check for duplicates
                    this.checkForDuplicates(result, fileHash);
                    
                    this.results.push(result);
                    console.log(`📄 Found: ${filePath} (Score: ${relevanceScore})`);
                    
                    return result;
                } catch (statError) {
                    console.log(`⚠️  File stats unavailable for ${filePath}: ${statError.message}`);
                }
            }
            
        } catch (error) {
            // Silently skip files we can't read
        }
        
        return null;
    }
    
    async getFileHash(filePath, fileSize) {
        // For performance, create a simple hash based on file size and path
        // For more accuracy, could use crypto.createHash() for actual content
        return `${fileSize}-${path.basename(filePath)}-${fileSize > 0 ? 'content' : 'empty'}`;
    }
    
    checkForDuplicates(fileResult, fileHash) {
        if (this.duplicates.has(fileHash)) {
            const existing = this.duplicates.get(fileHash);
            existing.push(fileResult.filePath);
        } else {
            this.duplicates.set(fileHash, [fileResult.filePath]);
        }
    }
    
    getVolumePath(filePath) {
        // Determine which volume this file belongs to
        if (os.platform() === 'win32') {
            return filePath.substring(0, 3); // C:\\ format
        } else if (filePath.startsWith('/Volumes/')) {
            const parts = filePath.split('/');
            return `/${parts[1]}/${parts[2]}`;
        } else {
            return '/'; // Root volume on Unix systems
        }
    }
    
    async generateEnhancedReport() {
        try {
            console.log('\\n📊 Generating comprehensive reports...');
            
            // Sort by relevance score (highest first)
            this.results.sort((a, b) => b.relevanceScore - a.relevanceScore);
            
            const finalStats = this.progress.getFinalStats();
            const duplicatesList = Array.from(this.duplicates.entries())
                .filter(([hash, paths]) => paths.length > 1)
                .map(([hash, paths]) => ({ hash, paths, count: paths.length }));
            
            // Generate detailed JSON report
            const detailedReport = {
                searchDate: new Date().toISOString(),
                searchStats: finalStats,
                totalFilesFound: this.results.length,
                duplicatesFound: duplicatesList.length,
                volumeStats: Object.fromEntries(this.volumeStats),
                keywordsUsed: CONFIG.KEYWORDS,
                results: this.results,
                duplicates: duplicatesList
            };
            
            // Generate summary JSON report
            const summaryReport = {
                searchDate: new Date().toISOString(),
                searchStats: finalStats,
                totalFilesFound: this.results.length,
                topFiles: this.results.slice(0, 50),
                duplicatesCount: duplicatesList.length,
                volumeStats: Object.fromEntries(this.volumeStats),
                keywordFrequency: this.getKeywordFrequency()
            };
            
            // Save reports
            await fs.writeFile(
                CONFIG.REPORTS.JSON_DETAILED,
                JSON.stringify(detailedReport, null, 2)
            );
            
            await fs.writeFile(
                CONFIG.REPORTS.JSON_SUMMARY,
                JSON.stringify(summaryReport, null, 2)
            );
            
            // Generate CSV for spreadsheet analysis
            await this.generateCSVReport();
            
            // Create enhanced markdown summary
            const markdown = this.createEnhancedSummaryReport(finalStats, duplicatesList);
            await fs.writeFile(CONFIG.REPORTS.MARKDOWN, markdown);
            
            console.log(`\\n🎬 ENHANCED SEARCH COMPLETE!`);
            console.log(`📁 Found ${this.results.length} relevant files across all volumes`);
            console.log(`🔄 Detected ${duplicatesList.length} duplicate file groups`);
            console.log(`⏱️  Total time: ${finalStats.totalTime}s at ${finalStats.averageRate} files/sec`);
            console.log(`\\n📄 Reports generated:`);
            console.log(`  📊 ${CONFIG.REPORTS.JSON_DETAILED}`);
            console.log(`  📋 ${CONFIG.REPORTS.JSON_SUMMARY}`);
            console.log(`  📝 ${CONFIG.REPORTS.MARKDOWN}`);
            console.log(`  📈 ${CONFIG.REPORTS.CSV_EXPORT}`);
            
        } catch (error) {
            console.error(`❌ Error generating report: ${error.message}`);
            throw error;
        }
    }
    
    async generateCSVReport() {
        const csvHeader = [
            'File Path', 'File Name', 'Extension', 'Relevance Score', 
            'Keywords', 'Size (KB)', 'Last Modified', 'Volume', 'Directory'
        ].join(',');
        
        const csvRows = this.results.map(file => [
            `"${file.filePath}"`,
            `"${file.fileName}"`,
            file.extension,
            file.relevanceScore,
            `"${file.matchedKeywords.join('; ')}"`,
            (file.size / 1024).toFixed(1),
            file.lastModified.toISOString().split('T')[0],
            `"${file.volumePath}"`,
            `"${file.directory}"`
        ].join(',')).join('\\n');
        
        await fs.writeFile(CONFIG.REPORTS.CSV_EXPORT, csvHeader + '\\n' + csvRows);
    }
    
    createEnhancedSummaryReport(stats, duplicates) {
        const topFiles = this.results.slice(0, 30);
        
        return `# Golden Wings Documentary - Enhanced Content Inventory
        
**Search Date:** ${new Date().toLocaleString()}
**Search Duration:** ${stats.totalTime} seconds
**Processing Rate:** ${stats.averageRate} files/second
**Total Files Found:** ${this.results.length}
**Volumes Searched:** ${this.volumeStats.size}
**Duplicates Detected:** ${duplicates.length}

## 🏆 TOP RELEVANCE FILES

${topFiles.map((file, i) => `
### ${i + 1}. ${file.fileName}
- **Path:** \\`${file.filePath}\\`
- **Volume:** ${file.volumePath}
- **Relevance Score:** ${file.relevanceScore}
- **Keywords:** ${file.matchedKeywords.join(', ')}
- **Last Modified:** ${file.lastModified.toLocaleDateString()}
- **Size:** ${(file.size / 1024).toFixed(1)} KB
`).join('\\n')}

## 💾 VOLUME STATISTICS

${Array.from(this.volumeStats.entries()).map(([volume, stats]) => `
### ${volume}
- **Files Processed:** ${stats.filesProcessed.toLocaleString()}
- **Matches Found:** ${stats.filesFound}
- **Search Duration:** ${((stats.duration || 0) / 1000).toFixed(1)}s
`).join('\\n')}

## 🔄 DUPLICATE FILES

${duplicates.slice(0, 10).map((dup, i) => `
### Duplicate Group ${i + 1} (${dup.count} copies)
${dup.paths.map(p => `- ${p}`).join('\\n')}
`).join('\\n')}

## 📊 FILE TYPE BREAKDOWN

${this.getFileTypeBreakdown()}

## 🔍 KEYWORD FREQUENCY

${this.getKeywordFrequency()}

## ⚙️ SEARCH CONFIGURATION

- **Max File Size:** ${(CONFIG.MAX_FILE_SIZE / 1024 / 1024).toFixed(0)}MB
- **Max Depth:** ${CONFIG.MAX_DEPTH} levels
- **Worker Threads:** ${CONFIG.WORKER_THREADS}
- **File Types:** ${CONFIG.SEARCH_EXTENSIONS.length} extensions
- **Keywords:** ${CONFIG.KEYWORDS.length} search terms

---

*Generated by Enhanced Golden Wings Content Hunter 🛫*
*Search completed at ${new Date().toLocaleString()}*
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
            .join('\\n');
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
            .slice(0, 20)
            .map(([keyword, count]) => `- **${keyword}**: ${count} mentions`)
            .join('\\n');
    }
    
    cleanup() {
        this.results = [];
        this.duplicates.clear();
        this.volumeStats.clear();
        this.processedPaths.clear();
        console.log('🧹 Cleanup completed - memory freed');
    }
    
    async hunt(configPath = null) {
        console.log('🚀 Starting Enhanced Golden Wings Content Hunt...');
        console.log(`🎯 Searching for ${CONFIG.KEYWORDS.length} keywords`);
        console.log(`📂 Using ${CONFIG.WORKER_THREADS} worker threads`);
        console.log(`💾 Multi-volume search enabled`);
        
        try {
            // Load external config if provided
            if (configPath) {
                await this.loadConfig(configPath);
            }
            
            // Start the comprehensive search
            await this.searchAllVolumes();
            
            // Generate all reports
            await this.generateEnhancedReport();
            
        } catch (error) {
            console.error(`❌ Hunt failed: ${error.message}`);
            throw error;
        }
    }
}

// Main execution
if (isMainThread) {
    // Check for config file argument
    const configPath = process.argv[2]; // node script.js config.json
    
    const hunter = new DocumentaryContentHunter();
    
    // Handle process termination gracefully
    process.on('SIGINT', () => {
        console.log('\\n🛑 Process interrupted. Cleaning up...');
        hunter.cleanup();
        process.exit(0);
    });
    
    process.on('SIGTERM', () => {
        console.log('\\n🛑 Process terminated. Cleaning up...');
        hunter.cleanup();
        process.exit(0);
    });
    
    // Run the enhanced hunt
    hunter.hunt(configPath)
        .then(() => {
            console.log('\\n🎉 Hunt completed successfully!');
            hunter.cleanup();
        })
        .catch(error => {
            console.error('❌ Hunt failed:', error.message);
            hunter.cleanup();
            process.exit(1);
        });
}

module.exports = { DocumentaryContentHunter, VolumeDetector };
''';

# Save the fixed script
with open('content-hunter-fixed.js', 'w', encoding='utf-8') as f:
    f.write(fixed_script)

print("✅ Fixed script created: content-hunter-fixed.js")
print("\nFixes applied:")
print("• Enhanced Windows volume detection with PowerShell fallback")
print("• Manual drive letter checking (A: through Z:)")
print("• Better error handling for volume detection failures")
print("• Fallback to user directories if volume detection completely fails")
print("• Added check for 0 volumes to prevent empty searches")