#!/usr/bin/env python3
"""
Simple AI Content Analyzer - No Hanging Version
Quickly analyzes file contents and suggests meaningful names
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

def analyze_file_content(file_path: str) -> Dict:
    """Quickly analyze file content and suggest a name"""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": "File not found", "confidence": 0.0}
        
        # Quick size check
        if file_path.stat().st_size > 500000:  # 500KB max
            return {"error": "File too large", "confidence": 0.0}
        
        # Read first 1000 characters only
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)
        except:
            return {"error": "Cannot read file", "confidence": 0.0}
        
        # Quick analysis
        content_lower = content.lower()
        extension = file_path.suffix
        
        # Detect content type
        if "chapter" in content_lower:
            return analyze_chapter(file_path.name, content, extension)
        elif "interview" in content_lower or "q:" in content_lower or "a:" in content_lower:
            return analyze_interview(file_path.name, content, extension)
        elif "transcript" in content_lower:
            return analyze_transcript(file_path.name, content, extension)
        elif "production" in content_lower or "edit" in content_lower:
            return analyze_production(file_path.name, content, extension)
        elif "golden wings" in content_lower or "boeing" in content_lower or "747" in content_lower:
            return analyze_golden_wings(file_path.name, content, extension)
        else:
            return analyze_generic(file_path.name, content, extension)
            
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}", "confidence": 0.0}

def analyze_chapter(filename: str, content: str, extension: str) -> Dict:
    """Analyze chapter content"""
    content_lower = content.lower()
    
    # Extract chapter number
    chapter_match = re.search(r'chapter\s+(\d+)', content_lower)
    chapter_num = chapter_match.group(1) if chapter_match else "X"
    
    # Extract title or key phrase
    title = "Chapter"
    lines = content.split('\n')[:5]
    for line in lines:
        line = line.strip()
        if len(line) > 10 and len(line) < 100 and line[0].isupper():
            title = line.replace("Chapter", "").strip()
            break
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    suggested_name = f"GW_Chapter_{chapter_num}_{title}_{date}{extension}"
    suggested_name = clean_filename(suggested_name)
    
    return {
        "content_type": "chapter",
        "suggested_name": suggested_name,
        "confidence": 0.9,
        "reasoning": [f"Detected chapter {chapter_num}: {title}"],
        "persons": extract_persons(content),
        "topics": ["golden_wings", "chapter", "documentary"]
    }

def analyze_interview(filename: str, content: str, extension: str) -> Dict:
    """Analyze interview content"""
    content_lower = content.lower()
    
    # Extract person names
    persons = extract_persons(content)
    person = persons[0] if persons else "Interviewee"
    
    # Extract topic
    topic = "Interview"
    if "golden wings" in content_lower:
        topic = "Golden_Wings"
    elif "boeing" in content_lower or "747" in content_lower:
        topic = "Aviation"
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    suggested_name = f"GW_Interview_{person}_{topic}_{date}{extension}"
    suggested_name = clean_filename(suggested_name)
    
    return {
        "content_type": "interview",
        "suggested_name": suggested_name,
        "confidence": 0.8,
        "reasoning": [f"Detected interview with {person.replace('Unknown', 'Speaker')} about {topic}"],
        "persons": persons,
        "topics": ["interview", "golden_wings", topic.lower()]
    }

def analyze_transcript(filename: str, content: str, extension: str) -> Dict:
    """Analyze transcript content"""
    content_lower = content.lower()
    
    # Determine transcript type
    transcript_type = "Conversation"
    if "interview" in content_lower:
        transcript_type = "Interview"
    elif "meeting" in content_lower:
        transcript_type = "Meeting"
    
    # Extract person
    persons = extract_persons(content)
    person = persons[0] if persons else "Speaker"
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    suggested_name = f"GW_Transcript_{transcript_type}_{person}_{date}{extension}"
    suggested_name = clean_filename(suggested_name)
    
    return {
        "content_type": "transcript",
        "suggested_name": suggested_name,
        "confidence": 0.8,
        "reasoning": [f"Detected {transcript_type} transcript with {person.replace('Unknown', 'Speaker')}"],
        "persons": persons,
        "topics": ["transcript", "golden_wings"]
    }

def analyze_production(filename: str, content: str, extension: str) -> Dict:
    """Analyze production content"""
    content_lower = content.lower()
    
    # Determine production type
    prod_type = "Edit"
    if "audio" in content_lower:
        prod_type = "Audio"
    elif "video" in content_lower:
        prod_type = "Video"
    elif "after effects" in content_lower:
        prod_type = "After_Effects"
    
    # Extract description
    description = "Production"
    if "fcp" in content_lower:
        description = "FCP"
    elif "ae" in content_lower:
        description = "After_Effects"
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    suggested_name = f"GW_Production_{prod_type}_{description}_{date}{extension}"
    suggested_name = clean_filename(suggested_name)
    
    return {
        "content_type": "production",
        "suggested_name": suggested_name,
        "confidence": 0.7,
        "reasoning": [f"Detected {prod_type} production content"],
        "persons": extract_persons(content),
        "topics": ["production", "golden_wings", prod_type.lower()]
    }

def analyze_golden_wings(filename: str, content: str, extension: str) -> Dict:
    """Analyze Golden Wings specific content"""
    content_lower = content.lower()
    
    # Extract key elements
    persons = extract_persons(content)
    meaningful_words = extract_meaningful_words(content, max_words=2)
    
    # Use meaningful words for description, or person name, or fallback
    if meaningful_words:
        description = "_".join(meaningful_words)
    elif persons:
        description = persons[0]
    else:
        description = "Documentary"
    
    # Determine content type
    content_type = "Document"
    if "chapter" in content_lower:
        content_type = "Chapter"
    elif "interview" in content_lower:
        content_type = "Interview"
    elif "transcript" in content_lower:
        content_type = "Transcript"
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    suggested_name = f"GW_{content_type}_{description}_{date}{extension}"
    suggested_name = clean_filename(suggested_name)
    
    reasoning = f"Golden Wings {content_type} content with: {', '.join(meaningful_words)}" if meaningful_words else f"Golden Wings {content_type} content"
    
    return {
        "content_type": "golden_wings",
        "suggested_name": suggested_name,
        "confidence": 0.8,
        "reasoning": [reasoning],
        "persons": persons,
        "topics": ["golden_wings", "documentary", "aviation"] + meaningful_words
    }

def analyze_generic(filename: str, content: str, extension: str) -> Dict:
    """Analyze generic content"""
    content_lower = content.lower()
    
    # Extract meaningful words from content
    meaningful_words = extract_meaningful_words(content, max_words=2)
    
    # Use meaningful words if available, otherwise clean filename
    if meaningful_words:
        content_desc = "_".join(meaningful_words)
    else:
        clean_name = re.sub(r'[^\w\s-]', '', filename)
        clean_name = re.sub(r'\s+', '_', clean_name)
        content_desc = clean_name
    
    # Extract date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', content)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    suggested_name = f"GW_Document_{content_desc}_{date}{extension}"
    suggested_name = clean_filename(suggested_name)
    
    reasoning = f"Content analysis found: {', '.join(meaningful_words)}" if meaningful_words else "Generic document analysis"
    
    return {
        "content_type": "generic",
        "suggested_name": suggested_name,
        "confidence": 0.6 if meaningful_words else 0.5,
        "reasoning": [reasoning],
        "persons": extract_persons(content),
        "topics": meaningful_words if meaningful_words else ["document"]
    }

def extract_meaningful_words(content: str, max_words: int = 3) -> List[str]:
    """Extract the most meaningful words from content, excluding common language"""
    import re
    from collections import Counter
    
    # Common words to exclude (stop words + common terms)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
        'what', 'when', 'where', 'why', 'how', 'who', 'which', 'whom', 'whose', 'if', 'then', 'else', 'because', 'so', 'as', 'than',
        'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now',
        'file', 'document', 'text', 'content', 'data', 'information', 'page', 'section', 'part', 'chapter', 'line', 'word', 'character',
        'time', 'date', 'year', 'month', 'day', 'hour', 'minute', 'second', 'today', 'yesterday', 'tomorrow',
        'here', 'there', 'where', 'everywhere', 'somewhere', 'nowhere', 'up', 'down', 'left', 'right', 'front', 'back', 'top', 'bottom',
        'good', 'bad', 'big', 'small', 'large', 'little', 'new', 'old', 'first', 'last', 'next', 'previous', 'other', 'another',
        'get', 'got', 'give', 'gave', 'take', 'took', 'make', 'made', 'go', 'went', 'come', 'came', 'see', 'saw', 'know', 'knew',
        'think', 'thought', 'say', 'said', 'tell', 'told', 'ask', 'asked', 'want', 'wanted', 'need', 'needed', 'like', 'liked', 'love', 'loved'
    }
    
    # Clean and tokenize content
    content_clean = re.sub(r'[^\w\s]', ' ', content.lower())
    words = re.findall(r'\b[a-z]{3,}\b', content_clean)  # Words with 3+ letters
    
    # Filter out stop words and count frequency
    meaningful_words = [word for word in words if word not in stop_words]
    word_counts = Counter(meaningful_words)
    
    # Get most common meaningful words
    most_common = word_counts.most_common(max_words)
    
    # Return the words (not counts)
    return [word.title() for word, count in most_common if count > 1]  # Only words that appear more than once

def extract_persons(content: str) -> List[str]:
    """Extract person names from content"""
    persons = []
    content_lower = content.lower()
    
    # Known persons
    known_persons = ["caleb", "stewart", "jay", "ricks", "jock", "bethune", "robyn"]
    
    for person in known_persons:
        if person in content_lower:
            persons.append(person.title())
    
    # Look for name patterns
    name_patterns = [
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
    ]
    
    for pattern in name_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if match not in persons:
                persons.append(match)
    
    return list(set(persons))

def clean_filename(filename: str) -> str:
    """Clean filename to avoid 'Unknown' at all costs"""
    # Replace any "Unknown" with better alternatives
    filename = filename.replace("Unknown", "Documentary")
    filename = filename.replace("unknown", "documentary")
    filename = filename.replace("UNKNOWN", "DOCUMENTARY")
    
    # Replace any remaining generic terms
    filename = filename.replace("General", "Content")
    filename = filename.replace("general", "content")
    
    return filename

def main():
    """Test the analyzer on a few files"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_ai_analyzer.py <file_path>")
        return
    
    file_path = sys.argv[1]
    print(f"🔍 Analyzing: {file_path}")
    
    result = analyze_file_content(file_path)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Suggested name: {result['suggested_name']}")
        print(f"📊 Confidence: {result['confidence']:.2f}")
        print(f"💭 Reasoning: {result['reasoning'][0]}")
        print(f"👥 Persons: {result['persons']}")
        print(f"🏷️  Topics: {result['topics']}")

if __name__ == "__main__":
    main()
