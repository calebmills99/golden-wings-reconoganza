# Golden Wings Naming Convention - Lessons Learned

## Phase 1 Issues Identified

### Issue 1: Festival Interview Context Loss
**Problem**: `Caleb_All_Around_Film_Festival_Interview.txt` → `Transcript_Unknown_Interview_Transcript.txt`
- **Root Cause**: Naming rules didn't recognize "All Around Film Festival" as a specific context
- **Impact**: Lost valuable festival-specific context information
- **Manual Fix Applied**: Renamed to `Transcript_Caleb_Stewart_All_Around_Film_Festival_Interview.txt` + added disclaimer

### Improved Rules for Phase 2:
```json
{
  "Condition": { "FileName": "(?i).*(film.*festival|festival.*interview).*" },
  "Mapping": { 
    "Person": "Caleb_Stewart", 
    "Topic": "Festival_Interview", 
    "Context": "Extract_Festival_Name" 
  }
}
```

### Additional Festival Pattern Rules Needed:
- All Around Film Festival
- Sundance submissions
- Local film festivals
- Industry showcases
- Award submissions

## Phase 2 Improvements for TOP 51-100

### Enhanced Interview Classification:
1. **Festival Interviews**: Preserve festival names in context
2. **Subject Interviews**: Better person identification from filenames
3. **Technical Interviews**: Distinguish between creative and technical discussions
4. **Historical Interviews**: Family/background vs. production content

### Pattern Recognition Improvements:
- Extract specific festival names from filenames
- Identify interview subjects more accurately
- Preserve important contextual information
- Handle multi-part interviews better

### Issue 2: Production History vs Subject Research Confusion
**Problem**: `Golden Wings History.txt` → `GW_Document_Historical_Background_Research.txt`
- **Root Cause**: System confused "film production history" with "subject matter research"
- **Impact**: Meta-documentary content misclassified as research material
- **Manual Fix Applied**: Rename to `GW_Document_Production_Film_Journey.txt`

### Content Type Distinction Needed:
- **Production Meta-Content**: Behind-the-scenes, film journey, director's notes
- **Subject Research**: Historical background about airlines, stewardesses, aviation
- **Personal Narrative**: Family stories, personal experiences
- **Technical Documentation**: Equipment, settings, workflow notes

## Action Items for Next 50 Files (TOP 51-100):
- [ ] Review TOP101-200.md for festival-related content
- [ ] Update naming_convention_config.json with festival patterns
- [ ] Add person identification rules for known subjects
- [ ] Test with smaller batch before full execution

## Quality Control Checklist:
- [ ] Review all interview transcript mappings manually
- [ ] Verify no important context is lost in generic naming
- [ ] Check for festival/event specific content
- [ ] Validate person identification accuracy

---
*Updated: September 27, 2025*
*Next Review: Before TOP 51-100 processing*
