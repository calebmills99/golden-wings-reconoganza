# Development Guide for Golden Wings Reconoganza

## Getting Started

This repository is set up to work with Cursor IDE's background agent for enhanced AI-powered development.

### Repository Setup
- **Remote Origin**: `https://github.com/calebmills99/golden-wings-reconoganza`
- **Project Goal**: Find and process text files

### Working with Cursor
This repository includes Cursor-specific configuration files:
- `.cursor-context`: Provides project context to the AI
- `.cursorrules`: Defines coding guidelines and AI behavior
- `.gitignore`: Excludes Cursor-specific files and common artifacts

### Development Workflow
1. Clone the repository to your local machine
2. Open the project in Cursor IDE
3. The background agent will automatically use the context files to understand the project
4. Start developing with AI assistance

### File Structure
```
golden-wings-reconoganza/
├── README.md              # Project overview
├── .cursor-context        # AI context file
├── .cursorrules          # AI behavior rules  
├── .gitignore            # Git ignore patterns
├── DEVELOPMENT.md        # This file
└── .git/                 # Git configuration
```

### Next Steps
- Add your text processing code
- Create example text files for testing
- Implement file discovery functionality
- Add documentation as you build

### Tips for Cursor IDE
- Use the AI chat to ask questions about the codebase
- The background agent will suggest relevant code completions
- Context files help the AI understand your project's specific needs
- Use `Ctrl/Cmd + K` for AI-powered inline editing