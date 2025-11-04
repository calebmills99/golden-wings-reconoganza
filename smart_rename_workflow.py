#!/usr/bin/env python3
"""
Smart Rename Workflow with AI Content Analysis
Integrates AI content analysis with the existing rename workflow
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from ai_content_analyzer import AIContentAnalyzer

def load_parsed_data(input_file: str) -> list:
    """Load parsed file data"""
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_files_with_ai(file_data: list, config_file: str = "ai_naming_config.json") -> dict:
    """Analyze files using AI content analysis"""
    analyzer = AIContentAnalyzer(config_file)
    
    results = {
        "analysis_timestamp": datetime.now().isoformat(),
        "total_files": len(file_data),
        "files_analyzed": 0,
        "files_failed": 0,
        "analyses": []
    }
    
    print(f"🤖 AI Content Analysis Starting...")
    print(f"📁 Analyzing {len(file_data)} files...")
    
    for i, file_info in enumerate(file_data, 1):
        file_path = file_info.get("path", "")
        rank = file_info.get("rank", i)
        original_name = Path(file_path).name if file_path else f"rank_{rank}"
        
        print(f"📄 [{i:3d}/{len(file_data)}] Analyzing: {original_name}")
        
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
            analysis = analyzer.analyze_file_content(file_path)
            analysis["original_path"] = file_path
            analysis["rank"] = rank
            analysis["original_name"] = original_name
            
            if "error" in analysis:
                results["files_failed"] += 1
                print(f"   ❌ Error: {analysis['error']}")
            else:
                results["files_analyzed"] += 1
                print(f"   ✅ {analysis['suggested_name']} (confidence: {analysis['confidence']:.2f})")
                if analysis["reasoning"]:
                    print(f"      💭 {analysis['reasoning'][0]}")
        
        results["analyses"].append(analysis)
    
    return results

def generate_smart_rename_plan(analysis_results: dict) -> dict:
    """Generate a smart rename plan based on AI analysis"""
    rename_plan = {
        "generated_timestamp": datetime.now().isoformat(),
        "total_operations": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
        "operations": []
    }
    
    print(f"\n🎯 Generating Smart Rename Plan...")
    
    for analysis in analysis_results["analyses"]:
        if "error" in analysis:
            continue
            
        confidence = analysis.get("confidence", 0.0)
        suggested_name = analysis.get("suggested_name", "")
        original_path = analysis.get("original_path", "")
        
        if not original_path or not suggested_name:
            continue
        
        # Categorize by confidence
        if confidence >= 0.8:
            rename_plan["high_confidence"] += 1
        elif confidence >= 0.5:
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
    
    print(f"📊 Rename Plan Summary:")
    print(f"   🟢 High Confidence (≥0.8): {rename_plan['high_confidence']} files")
    print(f"   🟡 Medium Confidence (0.5-0.8): {rename_plan['medium_confidence']} files")
    print(f"   🔴 Low Confidence (<0.5): {rename_plan['low_confidence']} files")
    
    return rename_plan

def generate_rename_script(rename_plan: dict, output_file: str):
    """Generate a Python script to execute the smart renames"""
    script_content = f'''#!/usr/bin/env python3
"""
Smart Rename Execution Script
Generated: {datetime.now().isoformat()}
Total Operations: {rename_plan["total_operations"]}
High Confidence: {rename_plan["high_confidence"]}
Medium Confidence: {rename_plan["medium_confidence"]}
Low Confidence: {rename_plan["low_confidence"]}
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def execute_smart_renames():
    """Execute the smart rename operations"""
    print("🤖 Smart Rename Execution Starting...")
    print(f"📊 Total operations: {rename_plan["total_operations"]}")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    operations = {rename_plan["operations"]}
    
    for i, op in enumerate(operations, 1):
        original_path = op["original_path"]
        new_name = op["new_name"]
        confidence = op["confidence"]
        reasoning = op.get("reasoning", [])
        
        print(f"\\n📄 [{i:3d}/{len(operations)}] {{Path(original_path).name}}")
        print(f"   🎯 → {{new_name}} (confidence: {{confidence:.2f}})")
        if reasoning:
            print(f"   💭 {{reasoning[0]}}")
        
        try:
            if not Path(original_path).exists():
                print(f"   ⚠️  Source file not found, skipping...")
                skipped_count += 1
                continue
            
            # Create destination path
            dest_dir = Path(original_path).parent
            dest_path = dest_dir / new_name
            
            # Check if destination already exists
            if dest_path.exists():
                print(f"   ⚠️  Destination already exists, skipping...")
                skipped_count += 1
                continue
            
            # Perform rename
            shutil.move(original_path, dest_path)
            print(f"   ✅ Renamed successfully")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {{str(e)}}")
            error_count += 1
    
    print(f"\\n📊 Execution Summary:")
    print(f"   ✅ Successful: {{success_count}}")
    print(f"   ❌ Errors: {{error_count}}")
    print(f"   ⚠️  Skipped: {{skipped_count}}")
    
    return success_count, error_count, skipped_count

if __name__ == "__main__":
    execute_smart_renames()
'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"💾 Smart rename script generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Smart Rename Workflow with AI Analysis")
    parser.add_argument("--input", required=True, help="Input JSON file with parsed file data")
    parser.add_argument("--output-dir", default=".", help="Output directory for results")
    parser.add_argument("--config", default="ai_naming_config.json", help="AI naming config file")
    parser.add_argument("--min-confidence", type=float, default=0.3, help="Minimum confidence threshold")
    
    args = parser.parse_args()
    
    # Load input data
    print(f"📁 Loading input data from: {args.input}")
    file_data = load_parsed_data(args.input)
    
    # Analyze files with AI
    analysis_results = analyze_files_with_ai(file_data, args.config)
    
    # Save analysis results
    analysis_output = Path(args.output_dir) / f"ai_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(analysis_output, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Analysis results saved to: {analysis_output}")
    
    # Generate smart rename plan
    rename_plan = generate_smart_rename_plan(analysis_results)
    
    # Filter by confidence threshold
    filtered_operations = [
        op for op in rename_plan["operations"] 
        if op["confidence"] >= args.min_confidence
    ]
    
    print(f"\\n🎯 Confidence Filtering:")
    print(f"   📊 Original operations: {len(rename_plan['operations'])}")
    print(f"   🎯 Filtered operations (≥{args.min_confidence}): {len(filtered_operations)}")
    
    rename_plan["operations"] = filtered_operations
    rename_plan["total_operations"] = len(filtered_operations)
    
    # Save rename plan
    plan_output = Path(args.output_dir) / f"smart_rename_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(plan_output, 'w', encoding='utf-8') as f:
        json.dump(rename_plan, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Smart rename plan saved to: {plan_output}")
    
    # Generate execution script
    script_output = Path(args.output_dir) / f"execute_smart_renames_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    generate_rename_script(rename_plan, script_output)
    
    print(f"\\n🎉 Smart Rename Workflow Complete!")
    print(f"📋 Next steps:")
    print(f"   1. Review the analysis results: {analysis_output}")
    print(f"   2. Review the rename plan: {plan_output}")
    print(f"   3. Execute the rename script: python {script_output}")

if __name__ == "__main__":
    main()
