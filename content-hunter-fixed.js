const fs = require('fs').promises;
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
    
    // Text-based file type support only (no media files)
    SEARCH_EXTENSIONS: [
        // Text documents
        '.md', '.txt', '.json', '.docx', '.doc', '.pdf', '.rtf',
        '.csv', '.log', '.notes', '.html', '.xml', '.yml', '.yaml',
        '.fountain', '.fdx', '.screenplay', '.final', '.draft'

        // Archive files removed - they don't contain readable text content
        // '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'
    ],
    
    // Performance settings
    MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB limit
    MAX_DEPTH: 4, // Reduced depth for faster search (was 8)
    WORKER_THREADS: Math.min(os.cpus().length, 4), // Use CPU cores efficiently
    BATCH_SIZE: 100, // Process files in batches
    
    // Target directories - PHYSICAL DRIVES ONLY (no cloud/network drives)
    TARGET_DIRECTORIES: [
        'C:\\',  // C: drive (system drive)
        'D:\\',  // D: drive (local storage)
        'E:\\',  // E: drive (Google Drive)
        'F:\\',  // F: drive (physical drive)
        'G:\\'   // G: drive (physical drive)
        // Explicitly excluding I:\\ (legacy Google Drive mapping) and other network/cloud drives
    ],
    
    // Search behavior
    SKIP_PATTERNS: [
        'node_modules', 'Library', 'System', 'Windows', 'Program Files',
        '.git', '.svn', '.DS_Store', 'Thumbs.db', '$Recycle.Bin',
        'quivr_parsed_data', 'powershell-configure-script',
        'System Volume Information', 'pagefile.sys', 'hiberfil.sys',
        // Exclude the content hunter's own directory to prevent self-referential results
        'golden-wings-reconoganza',
        // False positive exclusions
        'blackhat-python', 'Ethical Hacking', 'penetration-testing',
        'cybersecurity', 'hacking', 'exploit', 'breach', 'vhp',
        'Ayesha-osint-toolkit', 'DnsFilters', 'AdverseAdSiteList',
        // Cloud/Network drive exclusions (PHYSICAL DRIVES ONLY)
        'My Drive', 'Google Drive', 'OneDrive', 'Dropbox', 'iCloud'
    ],

    // Backup and temporary folder patterns
    BACKUP_PATTERNS: [
        'backup', 'backups', 'time machine', 'snapshots', 'versions',
        '.Trashes', 'Recycler', 'RECYCLER', 'temp', 'tmp', 'cache',
        // Additional false positive patterns
        'AppData', 'ProgramData', 'spell', 'api-metadata', 'cloud-code'
    ],
    
    // Output settings
    REPORTS: {
        JSON_DETAILED: 'golden-wings-content-inventory-detailed.json',
        JSON_SUMMARY: 'golden-wings-content-summary.json',
        MARKDOWN: 'CONTENT-SUMMARY.md',
        CSV_EXPORT: 'content-inventory.csv',
        TOP50: 'TOP50.md',
        TOP100: 'TOP100.md',
        TOP101_200: 'TOP101-200.md',
        TOP201_300: 'TOP201-300.md',
        CONTROL25_MD: 'CONTROL25.md',
        CONTROL25_JSON: 'control25.json'
    }
};

// --- .huntignore + output exclusion helpers ---
const HUNTIGNORE_PATH = path.join(process.cwd(), '.huntignore');

function globToRegex(glob) {
    // Convert simple .gitignore-like globs to a RegExp. Supports **, *, ?.
    // We match against full absolute paths, case-insensitive.
    let escaped = glob
        .replace(/[.+^${}()|[\]\\]/g, '\\$&') // escape regex specials
        .replace(/\*\*/g, '§§DOUBLESTAR§§');    // temp token for **

    escaped = escaped
        .replace(/\*/g, '[^\\/]*')             // *  => any non-sep chars
        .replace(/\?/g, '[^\\/]');             // ?  => any single non-sep

    escaped = escaped.replace(/§§DOUBLESTAR§§/g, '.*'); // ** => any depth

    // If pattern ends with a path separator, treat as directory with any depth
    if (/[\\\/]$/.test(glob)) {
        escaped += '.*';
    }

    return new RegExp('^' + escaped + '$', 'i');
}

async function loadHuntIgnore(filePath = HUNTIGNORE_PATH) {
    try {
        const raw = await fs.readFile(filePath, 'utf8');
        const lines = raw.split(/\r?\n/)
            .map(l => l.trim())
            .filter(l => l && !l.startsWith('#'));
        const regexes = [];
        for (const line of lines) {
            const normalized = line.replace(/[\\\/]+/g, path.sep);
            try {
                regexes.push(globToRegex(normalized));
            } catch {
                // ignore invalid pattern
            }
        }
        return regexes;
    } catch {
        return [];
    }
}

// Identify hunter’s own output files (exact filenames defined in CONFIG)
const OUTPUT_FILES = new Set(
    Object.values(CONFIG.REPORTS || {}).map(p => path.resolve(process.cwd(), p))
);

// Broader output families (timestamped variants, ranges, etc.)
const OUTPUT_GLOBS = [
    'golden-wings-content-*',
    'content_classification_results_*',
    'top*_*.json',
    'CONTENT-*.md',
    'TOP*.md',
    'content-inventory.csv',
    'CONTROL*.md',
    'control*.json'
].map(g => globToRegex(g.replace(/[\\\/]+/g, path.sep)));

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
                const drives = result.split('\r\n').filter(line => line.trim().match(/^[A-Z]:$/));
                volumes = drives.map(drive => drive.trim() + '\\');
                console.log(`📀 PowerShell detected drives: ${drives.join(', ')}`);
            } catch (psError) {
                console.log('⚠️  PowerShell method failed, trying alternative...');
                
                // Method 2: Manual drive letter checking
                const possibleDrives = ['A:', 'B:', 'C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:', 'Q:', 'R:', 'S:', 'T:', 'U:', 'V:', 'W:', 'X:', 'Y:', 'Z:'];
                
                for (const drive of possibleDrives) {
                    try {
                        const drivePath = drive + '\\';
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
            
            // Always ensure C: drive is included (where Desktop and user files are)
            if (!volumes.includes('C:\\')) {
                try {
                    await fs.access('C:\\');
                    volumes.unshift('C:\\'); // Add C: drive at the beginning
                    console.log(`✅ Added C: drive (Desktop/User files): C:\\`);
                } catch (error) {
                    console.log(`⚠️  C: drive not accessible: ${error.message}`);
                }
            }
            
            // If no volumes found, add common defaults
            if (volumes.length === 0) {
                const defaultDrives = ['C:\\', 'D:\\'];
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
            volumes = ['C:\\'];
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
        
        console.log(`\n📊 Progress: ${this.processedFiles} files processed | ${this.foundFiles} matches found`);
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
        this.huntIgnoreRegexes = [];
        this.results = [];
        this.duplicates = new Map();
        this.volumeStats = new Map();
        this.progress = new ProgressTracker();
        this.processedPaths = new Set(); // Prevent duplicate processing
        this.controlGroupMode = false; // When true, bypass .huntignore to form an unbiased control group
        
        // Load external config if provided
        if (configPath) {
            this.loadConfig(configPath);
        }
    }
    
    async init() {
        // Load .huntignore patterns once unless running control group
        if (this.controlGroupMode) {
            console.log('🧪 Control group mode enabled: bypassing .huntignore patterns');
            this.huntIgnoreRegexes = [];
            return;
        }
        this.huntIgnoreRegexes = await loadHuntIgnore();
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
        // Use PHYSICAL DRIVES ONLY - filter out cloud/network drives
        const targetDirs = CONFIG.TARGET_DIRECTORIES.filter(dir => {
            try {
                require('fs').accessSync(dir);
                // Additional check: skip if path contains cloud drive indicators
                const dirLower = dir.toLowerCase();
                if (dirLower.includes('my drive') || dirLower.includes('google drive') || 
                    dirLower.includes('onedrive') || dirLower.includes('dropbox') || 
                    dirLower.includes('icloud') || dir.startsWith('I:\\')) {
                    console.log(`🚫 Skipping cloud/network drive: ${dir}`);
                    return false;
                }
                return true;
            } catch {
                return false;
            }
        });
        
        console.log(`\n🎯 Starting PHYSICAL DRIVES search across ${targetDirs.length} directories`);
        console.log(`💽 Physical drives only: ${targetDirs.join(', ')}`);
        
        if (targetDirs.length === 0) {
            console.log('⚠️  No accessible physical drives found! Falling back to current directory.');
            targetDirs.push(process.cwd());
        }
        
        // Process directories in parallel with limited concurrency
        const concurrency = Math.min(targetDirs.length, 3);
        const promises = [];
        
        for (let i = 0; i < targetDirs.length; i += concurrency) {
            const batch = targetDirs.slice(i, i + concurrency);
            const batchPromises = batch.map(dir => this.searchVolume(dir));
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
        console.log(`\n💾 Searching volume: ${volumePath}`);
        
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
            
            console.log(`\n✅ Completed ${volumePath}: ${volumeStats.filesFound} files found`);
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
        // Normalize once
        const resolved = path.resolve(fullPath);
        
        // .huntignore (full-path match)
        try {
            const regexes = this.huntIgnoreRegexes || [];
            for (const rx of regexes) {
                if (rx.test(resolved)) return true;
            }
        } catch {}
        
        // Skip exact-known output files
        if (OUTPUT_FILES.has(resolved)) return true;
        
        // Skip output globs/families
        for (const rx of OUTPUT_GLOBS) {
            if (rx.test(resolved)) return true;
        }
        
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
            const textExtensions = ['.md', '.txt', '.json', '.html', '.xml', '.csv', '.log', '.docx', '.doc', '.pdf', '.rtf', '.yml', '.yaml', '.fountain', '.fdx', '.screenplay', '.final', '.draft'];
            
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

            // Skip overly high scores (likely self-generated artifacts)
            if (relevanceScore > 400) {
                console.log(`⏭️  Skipping ${filePath} (Score ${relevanceScore} > 400)`);
                return null;
            }
            
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
            return filePath.substring(0, 3); // C:\ format
        } else if (filePath.startsWith('/Volumes/')) {
            const parts = filePath.split('/');
            return `/${parts[1]}/${parts[2]}`;
        } else {
            return '/'; // Root volume on Unix systems
        }
    }
    
    async generateEnhancedReport() {
        try {
            console.log('\n📊 Generating comprehensive reports...');
            
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
            
            // Generate TOP 50 report
            await this.generateTop50Report();
            
            // Create enhanced markdown summary
            const markdown = this.createEnhancedSummaryReport(finalStats, duplicatesList);
            await fs.writeFile(CONFIG.REPORTS.MARKDOWN, markdown);
            
            console.log(`\n🎬 ENHANCED SEARCH COMPLETE!`);
            console.log(`📁 Found ${this.results.length} relevant files across all volumes`);
            console.log(`🔄 Detected ${duplicatesList.length} duplicate file groups`);
            console.log(`⏱️  Total time: ${finalStats.totalTime}s at ${finalStats.averageRate} files/sec`);
            console.log(`\n📄 Reports generated:`);
            console.log(`  📊 ${CONFIG.REPORTS.JSON_DETAILED}`);
            console.log(`  📋 ${CONFIG.REPORTS.JSON_SUMMARY}`);
            console.log(`  📝 ${CONFIG.REPORTS.MARKDOWN}`);
            console.log(`  📈 ${CONFIG.REPORTS.CSV_EXPORT}`);
            console.log(`  🏆 ${CONFIG.REPORTS.TOP50}`);
            
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
        ].join(',')).join('\n');
        
        await fs.writeFile(CONFIG.REPORTS.CSV_EXPORT, csvHeader + '\n' + csvRows);
    }
    
    async generateTop50Report() {
        const top50 = this.results.slice(0, 50);

        const markdown = `# 🏆 TOP 50 Golden Wings Content by Relevance Score

**Generated:** ${new Date().toLocaleString()}
**Total Files Found:** ${this.results.length}
**Search Duration:** ${this.progress.getFinalStats().totalTime}s

---

${top50.map((file, index) => {
    const rank = index + 1;
    const scoreBar = '█'.repeat(Math.max(1, Math.min(20, Math.floor(file.relevanceScore / 2))));
    const fileSize = file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'Unknown';
    const lastModified = file.lastModified ? file.lastModified.toLocaleDateString() : 'Unknown';

    return `## ${rank}. ${file.fileName}

**Score:** ${file.relevanceScore} ${scoreBar}
**Path:** \`${file.filePath}\`
**Volume:** ${file.volumePath}
**Size:** ${fileSize}
**Modified:** ${lastModified}
**Keywords:** ${file.matchedKeywords.join(', ')}
**Extension:** ${file.extension}

---`;
}).join('\n')}

## 📊 Score Distribution

${this.getScoreDistribution()}

## 🔍 Top Keywords in Results

${this.getTop50Keywords()}

---

*Generated by Golden Wings Content Hunter - Fixed Version*
*🎬 Finding documentary gold across your file system*
`;

        await fs.writeFile(CONFIG.REPORTS.TOP50, markdown);
    }

    async generateRangeReports() {
        // Generate TOP 100 (1-100)
        const top100 = this.results.slice(0, 100);
        await this.generateRangeReport(top100, 1, 100, 'TOP100.md');

        // Generate TOP 101-200 (if we have enough results)
        if (this.results.length > 100) {
            const range101_200 = this.results.slice(100, 200);
            await this.generateRangeReport(range101_200, 101, 200, 'TOP101-200.md');
        }

        // Generate TOP 201-300 (if we have enough results)
        if (this.results.length > 200) {
            const range201_300 = this.results.slice(200, 300);
            await this.generateRangeReport(range201_300, 201, 300, 'TOP201-300.md');
        }
    }

    async generateRangeReport(files, startRank, endRank, filename) {
        if (files.length === 0) return;

        const markdown = `# 🏆 TOP ${startRank}-${endRank} Golden Wings Content by Relevance Score

**Generated:** ${new Date().toLocaleString()}
**Total Files Found:** ${this.results.length}
**Search Duration:** ${this.progress.getFinalStats().totalTime}s
**Files in this range:** ${files.length}

---

${files.map((file, index) => {
    const rank = startRank + index;
    const scoreBar = '█'.repeat(Math.max(1, Math.min(20, Math.floor(file.relevanceScore / 2))));
    const fileSize = file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'Unknown';
    const lastModified = file.lastModified ? file.lastModified.toLocaleDateString() : 'Unknown';

    return `## ${rank}. ${file.fileName}

**Score:** ${file.relevanceScore} ${scoreBar}
**Path:** \`${file.filePath}\`
**Volume:** ${file.volumePath}
**Size:** ${fileSize}
**Modified:** ${lastModified}
**Keywords:** ${file.matchedKeywords.join(', ')}
**Extension:** ${file.extension}

---`;
}).join('\n')}

## 📊 Score Distribution (This Range)

${this.getScoreDistributionForRange(files)}

## 🔍 Top Keywords in This Range

${this.getTopKeywordsForRange(files)}

---

*Generated by Golden Wings Content Hunter - Fixed Version*
*🎬 Finding documentary gold across your file system*
`;

        const reportPath = CONFIG.REPORTS[filename.replace('.md', '').replace('-', '_').toUpperCase()];
        await fs.writeFile(reportPath, markdown);
    }

    getScoreDistributionForRange(files) {
        const ranges = [
            { min: 15, max: Infinity, label: '15+ (Exceptional)' },
            { min: 10, max: 14, label: '10-14 (High)' },
            { min: 5, max: 9, label: '5-9 (Medium)' },
            { min: 1, max: 4, label: '1-4 (Low)' }
        ];

        const distribution = ranges.map(range => {
            const count = files.filter(file =>
                file.relevanceScore >= range.min &&
                (range.max === Infinity || file.relevanceScore <= range.max)
            ).length;
            const percentage = files.length > 0 ? ((count / files.length) * 100).toFixed(1) : '0.0';
            const bar = '▓'.repeat(Math.floor(percentage / 2));

            return `- **${range.label}:** ${count} files (${percentage}%) ${bar}`;
        });

        return distribution.join('\n');
    }

    getTopKeywordsForRange(files) {
        const keywordCounts = {};

        files.forEach(file => {
            file.matchedKeywords.forEach(keyword => {
                keywordCounts[keyword] = (keywordCounts[keyword] || 0) + 1;
            });
        });

        return Object.entries(keywordCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 15)
            .map(([keyword, count]) => `- **${keyword}:** ${count} mentions`)
            .join('\n');
    }
    
    getScoreDistribution() {
        const ranges = [
            { min: 15, max: Infinity, label: '15+ (Exceptional)' },
            { min: 10, max: 14, label: '10-14 (High)' },
            { min: 5, max: 9, label: '5-9 (Medium)' },
            { min: 1, max: 4, label: '1-4 (Low)' }
        ];
        
        const distribution = ranges.map(range => {
            const count = this.results.filter(file => 
                file.relevanceScore >= range.min && 
                (range.max === Infinity || file.relevanceScore <= range.max)
            ).length;
            const percentage = ((count / this.results.length) * 100).toFixed(1);
            const bar = '▓'.repeat(Math.floor(percentage / 2));
            
            return `- **${range.label}:** ${count} files (${percentage}%) ${bar}`;
        });
        
        return distribution.join('\n');
    }
    
    getTop50Keywords() {
        const keywordCounts = {};
        const top50Files = this.results.slice(0, 50);
        
        top50Files.forEach(file => {
            file.matchedKeywords.forEach(keyword => {
                keywordCounts[keyword] = (keywordCounts[keyword] || 0) + 1;
            });
        });
        
        return Object.entries(keywordCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 15)
            .map(([keyword, count]) => `- **${keyword}:** ${count} mentions`)
            .join('\n');
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
- **Path:** \`${file.filePath}\`
- **Volume:** ${file.volumePath}
- **Relevance Score:** ${file.relevanceScore}
- **Keywords:** ${file.matchedKeywords.join(', ')}
- **Last Modified:** ${file.lastModified.toLocaleDateString()}
- **Size:** ${(file.size / 1024).toFixed(1)} KB
`).join('\n')}

## 💾 VOLUME STATISTICS

${Array.from(this.volumeStats.entries()).map(([volume, stats]) => `
### ${volume}
- **Files Processed:** ${stats.filesProcessed.toLocaleString()}
- **Matches Found:** ${stats.filesFound}
- **Search Duration:** ${((stats.duration || 0) / 1000).toFixed(1)}s
`).join('\n')}

## 🔄 DUPLICATE FILES

${duplicates.slice(0, 10).map((dup, i) => `
### Duplicate Group ${i + 1} (${dup.count} copies)
${dup.paths.map(p => `- ${p}`).join('\n')}
`).join('\n')}

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
            .slice(0, 20)
            .map(([keyword, count]) => `- **${keyword}**: ${count} mentions`)
            .join('\n');
    }
    
    cleanup() {
        this.results = [];
        this.duplicates.clear();
        this.volumeStats.clear();
        this.processedPaths.clear();
        console.log('🧹 Cleanup completed - memory freed');
    }

    async generateEnhancedReport() {
        console.log('📊 Generating comprehensive reports...');

        // Generate all report types
        await this.generateTop50Report();
        await this.generateRangeReports();

        // If control group mode is on, also generate the control group reports
        if (this.controlGroupMode) {
            await this.generateControlGroupReports();
        }

        console.log('✅ All reports generated successfully!');
    }

    // Select 25 legitimate high-scoring documents ignoring .huntignore
    selectControlGroup(limit = 25) {
        // Define legitimacy: score >= 10 and size >= 1KB
        const candidates = this.results
            .filter(f => (f.relevanceScore || 0) >= 10 && (f.size || 0) >= 1024)
            .sort((a, b) => {
                if (b.relevanceScore !== a.relevanceScore) return b.relevanceScore - a.relevanceScore;
                if ((b.size||0) !== (a.size||0)) return (b.size||0) - (a.size||0);
                const bt = b.lastModified ? new Date(b.lastModified).getTime() : 0;
                const at = a.lastModified ? new Date(a.lastModified).getTime() : 0;
                return bt - at;
            });

        // De-duplicate by fileHash then by path
        const seen = new Set();
        const unique = [];
        for (const f of candidates) {
            const key = (f.fileHash || '') + '|' + f.filePath;
            if (seen.has(key)) continue;
            seen.add(key);
            unique.push(f);
            if (unique.length >= limit) break;
        }
        return unique;
    }

    async generateControlGroupReports() {
        const control = this.selectControlGroup(25);

        const summary = {
            generated: new Date().toISOString(),
            criteria: {
                minRelevanceScore: 10,
                minSizeBytes: 1024,
                note: 'Control group bypasses .huntignore; still excludes self-generated outputs and skips absurdly high scores (>400).'
            },
            totalCandidates: this.results.length,
            selectedCount: control.length,
            items: control
        };

        // Write JSON
        await fs.writeFile(CONFIG.REPORTS.CONTROL25_JSON, JSON.stringify(summary, null, 2));

        // Write Markdown
        const md = `# 🎯 CONTROL GROUP (25) — High-Scoring Legitimate Documents

Generated: ${new Date().toLocaleString()}
Selection criteria: score ≥ 10, size ≥ 1KB, ignoring .huntignore rules
Total candidates found: ${this.results.length} | Selected: ${control.length}

---

${control.map((file, i) => {
    const rank = i + 1;
    const fileSize = file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'Unknown';
    const lastModified = file.lastModified ? new Date(file.lastModified).toLocaleDateString() : 'Unknown';
    return `## ${rank}. ${file.fileName}

**Score:** ${file.relevanceScore}
**Path:** \`${file.filePath}\`
**Volume:** ${file.volumePath}
**Size:** ${fileSize}
**Modified:** ${lastModified}
**Keywords:** ${file.matchedKeywords.join(', ')}
**Extension:** ${file.extension}

---`;
}).join('\n')}
`;
        await fs.writeFile(CONFIG.REPORTS.CONTROL25_MD, md);

        console.log(`🧪 Control group generated: ${CONFIG.REPORTS.CONTROL25_MD}, ${CONFIG.REPORTS.CONTROL25_JSON}`);
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
            
            // Initialize ignore rules
            await this.init();

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
    // Parse CLI arguments
    const args = process.argv.slice(2);
    let configPath = null;
    const hunter = new DocumentaryContentHunter();

    for (const arg of args) {
        if (arg === '--control25' || arg === '--control-group') {
            hunter.controlGroupMode = true;
        } else if (!arg.startsWith('-') && !configPath) {
            configPath = arg; // treat first non-flag as config path
        }
    }
    
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
    
    // Run the enhanced hunt
    hunter.hunt(configPath)
        .then(() => {
            console.log('\n🎉 Hunt completed successfully!');

            // Display generated reports
            console.log('\n📄 Reports generated:');
            console.log(`  📊 ${CONFIG.REPORTS.JSON_DETAILED}`);
            console.log(`  📋 ${CONFIG.REPORTS.JSON_SUMMARY}`);
            console.log(`  📝 ${CONFIG.REPORTS.MARKDOWN}`);
            console.log(`  📈 ${CONFIG.REPORTS.CSV_EXPORT}`);
            console.log(`  🏆 ${CONFIG.REPORTS.TOP50}`);
            console.log(`  🏆 ${CONFIG.REPORTS.TOP100}`);
            console.log(`  🏆 ${CONFIG.REPORTS.TOP101_200}`);
            console.log(`  🏆 ${CONFIG.REPORTS.TOP201_300}`);
            if (hunter.controlGroupMode) {
                console.log(`  🎯 ${CONFIG.REPORTS.CONTROL25_MD}`);
                console.log(`  🎯 ${CONFIG.REPORTS.CONTROL25_JSON}`);
            }

            hunter.cleanup();
        })
        .catch(error => {
            console.error('❌ Hunt failed:', error.message);
            hunter.cleanup();
            process.exit(1);
        });
}

module.exports = { DocumentaryContentHunter, VolumeDetector };
