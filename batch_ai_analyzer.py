#!/usr/bin/env python3
"""
Batch AI Content Analyzer
Processes multiple files and generates smart rename suggestions
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from simple_ai_analyzer import analyze_file_content

def process_file_list(file_data: dict) -> dict:
    """Process a list of files with AI analysis"""
    # Extract the files list from the parsed data structure
    files = file_data.get("files", [])
    
    results = {
        "analysis_timestamp": datetime.now().isoformat(),
        "total_files": len(files),
        "files_analyzed": 0,
        "files_failed": 0,
        "analyses": []
    }
    
    print(f"🤖 Batch AI Analysis Starting...")
    print(f"📁 Processing {len(files)} files...")
    
    for i, file_info in enumerate(files, 1):
        file_path = file_info.get("path", "")
        rank = file_info.get("rank", i)
        original_name = Path(file_path).name if file_path else f"rank_{rank}"
        
        print(f"📄 [{i:3d}/{len(files)}] {original_name}")
        
        if not file_path or not Path(file_path).exists():
            analysis = {
                "original_path": file_path,
                "rank": rank,
                "original_name": original_name,
                "error": "File not found",
                "confidence": 0.0,
                "suggested_name": f"Missing_File_{rank}_{datetime.now().strftime('%Y-%m-%d')}.txt"
            }
            results["files_failed"] += 1
            print(f"   ❌ File not found")
        else:
            analysis = analyze_file_content(file_path)
            analysis["original_path"] = file_path
            analysis["rank"] = rank
            analysis["original_name"] = original_name
            
            if "error" in analysis:
                results["files_failed"] += 1
                print(f"   ❌ {analysis['error']}")
            else:
                results["files_analyzed"] += 1
                print(f"   ✅ {analysis['suggested_name']}")
                print(f"      📊 Confidence: {analysis['confidence']:.2f}")
                if analysis.get("reasoning"):
                    print(f"      💭 {analysis['reasoning'][0]}")
        
        results["analyses"].append(analysis)
    
    return results

def generate_smart_rename_plan(analysis_results: dict, min_confidence: float = 0.5) -> dict:
    """Generate a smart rename plan based on AI analysis"""
    rename_plan = {
        "generated_timestamp": datetime.now().isoformat(),
        "min_confidence_threshold": min_confidence,
        "total_operations": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
        "operations": []
    }
    
    print(f"\n🎯 Generating Smart Rename Plan (min confidence: {min_confidence})...")
    
    for analysis in analysis_results["analyses"]:
        if "error" in analysis:
            continue
            
        confidence = analysis.get("confidence", 0.0)
        suggested_name = analysis.get("suggested_name", "")
        original_path = analysis.get("original_path", "")
        
        if not original_path or not suggested_name or confidence < min_confidence:
            continue
        
        # Categorize by confidence
        if confidence >= 0.8:
            rename_plan["high_confidence"] += 1
        elif confidence >= 0.6:
            rename_plan["medium_confidence"] += 1
        else:
            rename_plan["low_confidence"] += 1
        
        operation = {
            "original_path": original_path,
            "new_name": suggested_name,
            "confidence": confidence,
            "reasoning": analysis.get("reasoning", []),
            "content_type": analysis.get("content_type", "unknown"),
            "persons": analysis.get("persons", []),
            "topics": analysis.get("topics", [])
        }
        
        rename_plan["operations"].append(operation)
        rename_plan["total_operations"] += 1
    
    # Sort by confidence (highest first)
    rename_plan["operations"].sort(key=lambda x: x["confidence"], reverse=True)
    
    print(f"📊 Smart Rename Plan Summary:")
    print(f"   🟢 High Confidence (≥0.8): {rename_plan['high_confidence']} files")
    print(f"   🟡 Medium Confidence (0.6-0.8): {rename_plan['medium_confidence']} files")
    print(f"   🔴 Low Confidence (0.5-0.6): {rename_plan['low_confidence']} files")
    print(f"   📋 Total operations: {rename_plan['total_operations']}")
    
    return rename_plan

def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_ai_analyzer.py <input_json> [min_confidence]")
        print("Example: python batch_ai_analyzer.py top101_200_parsed.json 0.6")
        return
    
    input_file = sys.argv[1]
    min_confidence = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    
    print(f"📁 Loading input data from: {input_file}")
    
    # Load input data
    with open(input_file, 'r', encoding='utf-8') as f:
        file_data = json.load(f)
    
    # Process files with AI analysis
    analysis_results = process_file_list(file_data)
    
    # Save analysis results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    analysis_output = f"ai_analysis_{timestamp}.json"
    
    with open(analysis_output, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Analysis results saved to: {analysis_output}")
    
    # Generate smart rename plan
    rename_plan = generate_smart_rename_plan(analysis_results, min_confidence)
    
    # Save rename plan
    plan_output = f"smart_rename_plan_{timestamp}.json"
    
    with open(plan_output, 'w', encoding='utf-8') as f:
        json.dump(rename_plan, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Smart rename plan saved to: {plan_output}")
    
    # Show top suggestions
    print(f"\n🎯 Top 10 Smart Name Suggestions:")
    for i, op in enumerate(rename_plan["operations"][:10], 1):
        original_name = Path(op["original_path"]).name
        print(f"   {i:2d}. {original_name}")
        print(f"       → {op['new_name']}")
        print(f"       📊 Confidence: {op['confidence']:.2f}")
        if op["reasoning"]:
            print(f"       💭 {op['reasoning'][0]}")
        print()
    
    print(f"🎉 Batch AI Analysis Complete!")
    print(f"📋 Next steps:")
    print(f"   1. Review the analysis: {analysis_output}")
    print(f"   2. Review the rename plan: {plan_output}")
    print(f"   3. Execute smart renames if satisfied")

if __name__ == "__main__":
    main()
