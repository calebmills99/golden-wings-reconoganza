#!/usr/bin/env python3
"""
Analyze Current Renamed Files
Analyzes the currently renamed files and suggests better names
"""

import json
import os
from pathlib import Path
from datetime import datetime
from simple_ai_analyzer import analyze_file_content

def find_renamed_files(base_dir: str) -> list:
    """Find all renamed files in the directory"""
    files = []
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"❌ Directory not found: {base_dir}")
        return files
    
    # Look for GW_ prefixed files
    for file_path in base_path.rglob("GW_*"):
        if file_path.is_file():
            files.append({
                "path": str(file_path),
                "name": file_path.name,
                "size": file_path.stat().st_size
            })
    
    return files

def analyze_renamed_files(files: list) -> dict:
    """Analyze renamed files and suggest better names"""
    results = {
        "analysis_timestamp": datetime.now().isoformat(),
        "total_files": len(files),
        "files_analyzed": 0,
        "files_failed": 0,
        "analyses": []
    }
    
    print(f"🤖 Analyzing {len(files)} renamed files...")
    
    for i, file_info in enumerate(files, 1):
        file_path = file_info["path"]
        file_name = file_info["name"]
        
        print(f"📄 [{i:3d}/{len(files)}] {file_name}")
        
        analysis = analyze_file_content(file_path)
        analysis["original_path"] = file_path
        analysis["current_name"] = file_name
        
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

def generate_improvement_plan(analysis_results: dict, min_confidence: float = 0.6) -> dict:
    """Generate a plan to improve the current file names"""
    improvement_plan = {
        "generated_timestamp": datetime.now().isoformat(),
        "min_confidence_threshold": min_confidence,
        "total_improvements": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
        "improvements": []
    }
    
    print(f"\n🎯 Generating Improvement Plan (min confidence: {min_confidence})...")
    
    for analysis in analysis_results["analyses"]:
        if "error" in analysis:
            continue
        
        current_name = analysis.get("current_name", "")
        suggested_name = analysis.get("suggested_name", "")
        confidence = analysis.get("confidence", 0.0)
        
        # Only suggest improvements if the new name is significantly better
        if confidence < min_confidence or current_name == suggested_name:
            continue
        
        # Categorize by confidence
        if confidence >= 0.8:
            improvement_plan["high_confidence"] += 1
        elif confidence >= 0.6:
            improvement_plan["medium_confidence"] += 1
        else:
            improvement_plan["low_confidence"] += 1
        
        improvement = {
            "current_path": analysis["original_path"],
            "current_name": current_name,
            "suggested_name": suggested_name,
            "confidence": confidence,
            "reasoning": analysis.get("reasoning", []),
            "content_type": analysis.get("content_type", "unknown"),
            "persons": analysis.get("persons", []),
            "topics": analysis.get("topics", [])
        }
        
        improvement_plan["improvements"].append(improvement)
        improvement_plan["total_improvements"] += 1
    
    # Sort by confidence (highest first)
    improvement_plan["improvements"].sort(key=lambda x: x["confidence"], reverse=True)
    
    print(f"📊 Improvement Plan Summary:")
    print(f"   🟢 High Confidence (≥0.8): {improvement_plan['high_confidence']} files")
    print(f"   🟡 Medium Confidence (0.6-0.8): {improvement_plan['medium_confidence']} files")
    print(f"   🔴 Low Confidence (0.5-0.6): {improvement_plan['low_confidence']} files")
    print(f"   📋 Total improvements: {improvement_plan['total_improvements']}")
    
    return improvement_plan

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_current_files.py <directory> [min_confidence]")
        print("Example: python analyze_current_files.py 'D:\\Golden_Wings_Archive' 0.6")
        return
    
    directory = sys.argv[1]
    min_confidence = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    
    print(f"📁 Scanning directory: {directory}")
    
    # Find renamed files
    files = find_renamed_files(directory)
    
    if not files:
        print("❌ No renamed files found!")
        return
    
    print(f"📊 Found {len(files)} renamed files")
    
    # Analyze files
    analysis_results = analyze_renamed_files(files)
    
    # Save analysis results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    analysis_output = f"current_files_analysis_{timestamp}.json"
    
    with open(analysis_output, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Analysis results saved to: {analysis_output}")
    
    # Generate improvement plan
    improvement_plan = generate_improvement_plan(analysis_results, min_confidence)
    
    # Save improvement plan
    plan_output = f"file_improvement_plan_{timestamp}.json"
    
    with open(plan_output, 'w', encoding='utf-8') as f:
        json.dump(improvement_plan, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Improvement plan saved to: {plan_output}")
    
    # Show top improvements
    if improvement_plan["improvements"]:
        print(f"\n🎯 Top 10 Name Improvements:")
        for i, improvement in enumerate(improvement_plan["improvements"][:10], 1):
            print(f"   {i:2d}. {improvement['current_name']}")
            print(f"       → {improvement['suggested_name']}")
            print(f"       📊 Confidence: {improvement['confidence']:.2f}")
            if improvement["reasoning"]:
                print(f"       💭 {improvement['reasoning'][0]}")
            print()
    else:
        print(f"\n✅ No improvements needed! All files have good names.")
    
    print(f"🎉 Analysis Complete!")
    print(f"📋 Next steps:")
    print(f"   1. Review the analysis: {analysis_output}")
    print(f"   2. Review the improvement plan: {plan_output}")
    print(f"   3. Apply improvements if satisfied")

if __name__ == "__main__":
    main()
