#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

console.log('🦅 Golden Wings Content Hunter 🦅');
console.log('Searching for Golden Wings documentary related files...\n');

// File extensions related to documentary content
const documentaryExtensions = [
  '.txt', '.md', '.doc', '.docx', '.pdf',  // Text documents
  '.mp4', '.avi', '.mov', '.mkv', '.wmv',  // Video files
  '.mp3', '.wav', '.aac', '.flac',         // Audio files
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', // Images
  '.srt', '.vtt', '.ass',                  // Subtitle files
  '.json', '.xml', '.csv'                  // Data files
];

// Keywords related to Golden Wings documentary
const goldenWingsKeywords = [
  'golden-wings', 'goldenwings', 'golden wings',
  'documentary', 'reconoganza', 'interview',
  'script', 'transcript', 'notes'
];

function searchDirectory(dir, results = []) {
  try {
    const items = fs.readdirSync(dir);
    
    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stats = fs.statSync(fullPath);
      
      if (stats.isDirectory()) {
        // Skip .git and node_modules directories
        if (item !== '.git' && item !== 'node_modules') {
          searchDirectory(fullPath, results);
        }
      } else if (stats.isFile()) {
        const ext = path.extname(item).toLowerCase();
        const filename = item.toLowerCase();
        
        // Check if file extension is relevant or filename contains keywords
        const hasRelevantExtension = documentaryExtensions.includes(ext);
        const hasGoldenWingsKeyword = goldenWingsKeywords.some(keyword => 
          filename.includes(keyword.toLowerCase())
        );
        
        if (hasRelevantExtension || hasGoldenWingsKeyword) {
          results.push({
            path: fullPath,
            name: item,
            size: stats.size,
            extension: ext,
            modified: stats.mtime.toISOString(),
            matchReason: hasGoldenWingsKeyword ? 'keyword match' : 'file type match'
          });
        }
      }
    }
  } catch (error) {
    console.error(`Error reading directory ${dir}:`, error.message);
  }
  
  return results;
}

function displayResults(results) {
  if (results.length === 0) {
    console.log('❌ No Golden Wings documentary files found.');
    return;
  }
  
  console.log(`✅ Found ${results.length} Golden Wings documentary related file(s):\n`);
  
  results.forEach((file, index) => {
    console.log(`${index + 1}. ${file.name}`);
    console.log(`   📁 Path: ${file.path}`);
    console.log(`   📊 Size: ${file.size} bytes`);
    console.log(`   📅 Modified: ${file.modified}`);
    console.log(`   🎯 Match: ${file.matchReason}`);
    console.log('');
  });
  
  // Summary by file type
  const byExtension = {};
  results.forEach(file => {
    const ext = file.extension || 'no extension';
    byExtension[ext] = (byExtension[ext] || 0) + 1;
  });
  
  console.log('📈 Summary by file type:');
  Object.entries(byExtension).forEach(([ext, count]) => {
    console.log(`   ${ext}: ${count} file(s)`);
  });
}

// Main execution
const startTime = Date.now();
const searchPath = process.cwd();

console.log(`Searching in: ${searchPath}\n`);

const results = searchDirectory(searchPath);
displayResults(results);

const endTime = Date.now();
console.log(`\n⏱️  Search completed in ${endTime - startTime}ms`);