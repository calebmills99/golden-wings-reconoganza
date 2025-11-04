#!/usr/bin/env python3
"""
AI Content Analyzer for Golden Wings Documentary Files
Analyzes file contents and generates intelligent, meaningful names
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse

class AIContentAnalyzer:
    def __init__(self, config_file: str = "ai_naming_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """Load AI naming configuration"""
        default_config = {
            "max_file_size": 1024 * 1024,  # 1MB max for content analysis
            "content_sample_size": 2000,   # Characters to sample from large files
            "naming_patterns": {
                "interview": {
                    "keywords": ["interview", "question", "answer", "q:", "a:", "interviewee", "interviewer"],
                    "pattern": "Interview_{Person}_{Topic}_{Date}",
                    "min_confidence": 0.7
                },
                "chapter": {
                    "keywords": ["chapter", "episode", "part", "section", "story", "narrative"],
                    "pattern": "Chapter_{Number}_{Title}_{Date}",
                    "min_confidence": 0.8
                },
                "transcript": {
                    "keywords": ["transcript", "conversation", "dialogue", "speaking", "said", "told"],
                    "pattern": "Transcript_{Type}_{Person}_{Date}",
                    "min_confidence": 0.7
                },
                "production": {
                    "keywords": ["production", "edit", "cut", "scene", "shot", "footage", "audio", "video"],
                    "pattern": "Production_{Type}_{Description}_{Date}",
                    "min_confidence": 0.6
                },
                "research": {
                    "keywords": ["research", "study", "analysis", "findings", "data", "report"],
                    "pattern": "Research_{Topic}_{Type}_{Date}",
                    "min_confidence": 0.7
                }
            },
            "person_names": [
                "Caleb", "Stewart", "Jay", "Ricks", "Jock", "Bethune", "Robyn", 
                "Stewart_Family", "Golden_Wings", "Boeing", "747"
            ],
            "topics": [
                "aviation", "aircraft", "boeing", "747", "airline", "pilot", "flight",
                "documentary", "film", "production", "interview", "story", "history"
            ]
        }
        
        if Path(self.config_file).exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return {**default_config, **json.load(f)}
        return default_config
    
    def analyze_file_content(self, file_path: str) -> Dict:
        """Analyze file content and extract meaningful information"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"error": "File not found", "confidence": 0.0}
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.config["max_file_size"]:
                return {"error": "File too large for analysis", "confidence": 0.0}
            
            # Read file content
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except:
                return {"error": "Cannot read file content", "confidence": 0.0}
            
            # Sample content if too large
            if len(content) > self.config["content_sample_size"]:
                content = content[:self.config["content_sample_size"]] + "..."
            
            # Analyze content
            analysis = {
                "file_type": self.detect_file_type(content),
                "content_type": self.detect_content_type(content),
                "persons": self.extract_persons(content),
                "topics": self.extract_topics(content),
                "dates": self.extract_dates(content),
                "key_phrases": self.extract_key_phrases(content),
                "confidence": 0.0,
                "suggested_name": "",
                "reasoning": []
            }
            
            # Generate suggested name
            suggested_name, confidence, reasoning = self.generate_smart_name(
                file_path.name, content, analysis
            )
            
            analysis["suggested_name"] = suggested_name
            analysis["confidence"] = confidence
            analysis["reasoning"] = reasoning
            
            return analysis
            
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}", "confidence": 0.0}
    
    def detect_file_type(self, content: str) -> str:
        """Detect the type of file based on content patterns"""
        content_lower = content.lower()
        
        if re.search(r'<html|<body|<head', content_lower):
            return "html"
        elif re.search(r'\{.*\}', content) and re.search(r'"\w+"\s*:', content):
            return "json"
        elif re.search(r'<xml|<root', content_lower):
            return "xml"
        elif re.search(r'^\s*\d+\.\d+\.\d+', content, re.MULTILINE):
            return "log"
        else:
            return "text"
    
    def detect_content_type(self, content: str) -> str:
        """Detect the type of content (interview, chapter, etc.)"""
        content_lower = content.lower()
        scores = {}
        
        for content_type, config in self.config["naming_patterns"].items():
            score = 0
            for keyword in config["keywords"]:
                score += content_lower.count(keyword.lower())
            scores[content_type] = score
        
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0:
                return best_type
        
        return "unknown"
    
    def extract_persons(self, content: str) -> List[str]:
        """Extract person names from content"""
        persons = []
        content_lower = content.lower()
        
        for person in self.config["person_names"]:
            if person.lower() in content_lower:
                persons.append(person)
        
        # Look for common name patterns
        name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z][a-z]+_[A-Z][a-z]+\b',  # First_Last
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match not in persons:
                    persons.append(match)
        
        return list(set(persons))
    
    def extract_topics(self, content: str) -> List[str]:
        """Extract topics from content"""
        topics = []
        content_lower = content.lower()
        
        for topic in self.config["topics"]:
            if topic.lower() in content_lower:
                topics.append(topic)
        
        return list(set(topics))
    
    def extract_dates(self, content: str) -> List[str]:
        """Extract dates from content"""
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b\d{2}/\d{2}/\d{4}\b',  # MM/DD/YYYY
            r'\b\d{4}\b',              # YYYY
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            dates.extend(matches)
        
        return list(set(dates))
    
    def extract_key_phrases(self, content: str) -> List[str]:
        """Extract key phrases from content"""
        # Look for quoted text, titles, or important phrases
        phrases = []
        
        # Quoted text
        quoted = re.findall(r'"([^"]+)"', content)
        phrases.extend(quoted[:3])  # First 3 quotes
        
        # Lines that look like titles (short, capitalized)
        lines = content.split('\n')
        for line in lines[:10]:  # First 10 lines
            line = line.strip()
            if 10 < len(line) < 100 and line[0].isupper():
                phrases.append(line)
        
        return phrases[:5]  # Top 5 phrases
    
    def generate_smart_name(self, original_name: str, content: str, analysis: Dict) -> Tuple[str, float, List[str]]:
        """Generate a smart, meaningful name based on content analysis"""
        reasoning = []
        confidence = 0.0
        
        # Get file extension
        extension = Path(original_name).suffix
        
        # Determine content type and generate name
        content_type = analysis["content_type"]
        persons = analysis["persons"]
        topics = analysis["topics"]
        dates = analysis["dates"]
        
        if content_type == "interview":
            person = persons[0] if persons else "Unknown"
            topic = topics[0] if topics else "Interview"
            date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
            suggested_name = f"Interview_{person}_{topic}_{date}{extension}"
            confidence = 0.8
            reasoning.append(f"Detected interview content with {person}")
            
        elif content_type == "chapter":
            # Try to extract chapter number
            chapter_match = re.search(r'chapter\s+(\d+)', content.lower())
            chapter_num = chapter_match.group(1) if chapter_match else "Unknown"
            
            # Try to extract chapter title
            title = "Chapter"
            for phrase in analysis["key_phrases"]:
                if len(phrase) < 50 and "chapter" in phrase.lower():
                    title = phrase.replace("Chapter", "").strip()
                    break
            
            date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
            suggested_name = f"Chapter_{chapter_num}_{title}_{date}{extension}"
            confidence = 0.9
            reasoning.append(f"Detected chapter {chapter_num}: {title}")
            
        elif content_type == "transcript":
            transcript_type = "Conversation"
            if "interview" in content.lower():
                transcript_type = "Interview"
            elif "meeting" in content.lower():
                transcript_type = "Meeting"
            
            person = persons[0] if persons else "Unknown"
            date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
            suggested_name = f"Transcript_{transcript_type}_{person}_{date}{extension}"
            confidence = 0.8
            reasoning.append(f"Detected {transcript_type} transcript")
            
        elif content_type == "production":
            prod_type = "Edit"
            if "audio" in content.lower():
                prod_type = "Audio"
            elif "video" in content.lower():
                prod_type = "Video"
            
            description = topics[0] if topics else "Production"
            date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
            suggested_name = f"Production_{prod_type}_{description}_{date}{extension}"
            confidence = 0.7
            reasoning.append(f"Detected {prod_type} production content")
            
        elif content_type == "research":
            topic = topics[0] if topics else "General"
            research_type = "Analysis"
            if "report" in content.lower():
                research_type = "Report"
            
            date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
            suggested_name = f"Research_{topic}_{research_type}_{date}{extension}"
            confidence = 0.7
            reasoning.append(f"Detected research content on {topic}")
            
        else:
            # Fallback to intelligent analysis
            if persons:
                person = persons[0]
                topic = topics[0] if topics else "Document"
                date = dates[0] if dates else datetime.now().strftime("%Y-%m-%d")
                suggested_name = f"Document_{person}_{topic}_{date}{extension}"
                confidence = 0.6
                reasoning.append(f"Found content related to {person}")
            else:
                # Use key phrase or original name
                if analysis["key_phrases"]:
                    phrase = analysis["key_phrases"][0][:30]  # First 30 chars
                    suggested_name = f"Document_{phrase}_{datetime.now().strftime('%Y-%m-%d')}{extension}"
                    confidence = 0.5
                    reasoning.append(f"Using key phrase: {phrase}")
                else:
                    # Clean up original name
                    clean_name = re.sub(r'[^\w\s-]', '', original_name)
                    clean_name = re.sub(r'\s+', '_', clean_name)
                    suggested_name = f"Document_{clean_name}{extension}"
                    confidence = 0.3
                    reasoning.append("Using cleaned original name")
        
        # Add context from Golden Wings project
        if any(topic in content.lower() for topic in ["golden wings", "boeing", "747", "aviation"]):
            suggested_name = f"GW_{suggested_name}"
            confidence += 0.1
            reasoning.append("Golden Wings project content detected")
        
        return suggested_name, min(confidence, 1.0), reasoning

def main():
    parser = argparse.ArgumentParser(description="AI Content Analyzer for Golden Wings Files")
    parser.add_argument("--input", required=True, help="Input JSON file with file list")
    parser.add_argument("--output", required=True, help="Output JSON file for analysis results")
    parser.add_argument("--config", default="ai_naming_config.json", help="AI naming config file")
    
    args = parser.parse_args()
    
    analyzer = AIContentAnalyzer(args.config)
    
    # Load input file list
    with open(args.input, 'r', encoding='utf-8') as f:
        file_data = json.load(f)
    
    results = {
        "analysis_timestamp": datetime.now().isoformat(),
        "total_files": len(file_data),
        "files_analyzed": 0,
        "files_failed": 0,
        "analyses": []
    }
    
    print(f"🔍 AI Content Analysis Starting...")
    print(f"📁 Analyzing {len(file_data)} files...")
    
    for i, file_info in enumerate(file_data, 1):
        file_path = file_info.get("path", "")
        rank = file_info.get("rank", i)
        
        print(f"📄 [{i:3d}/{len(file_data)}] Analyzing: {Path(file_path).name}")
        
        analysis = analyzer.analyze_file_content(file_path)
        analysis["original_path"] = file_path
        analysis["rank"] = rank
        analysis["original_name"] = Path(file_path).name
        
        results["analyses"].append(analysis)
        
        if "error" in analysis:
            results["files_failed"] += 1
            print(f"   ❌ Error: {analysis['error']}")
        else:
            results["files_analyzed"] += 1
            print(f"   ✅ {analysis['suggested_name']} (confidence: {analysis['confidence']:.2f})")
            if analysis["reasoning"]:
                print(f"      💭 {analysis['reasoning'][0]}")
    
    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Analysis Complete!")
    print(f"✅ Files analyzed: {results['files_analyzed']}")
    print(f"❌ Files failed: {results['files_failed']}")
    print(f"💾 Results saved to: {args.output}")

if __name__ == "__main__":
    main()
