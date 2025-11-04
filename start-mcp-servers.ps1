# start-mcp-servers.ps1
# Launch all MCP servers in parallel using cmd /c

$mcpServers = @{
  github              = "npx -y github-mcp-server"
  context7            = "npx -y @upstash/context7-mcp"
  filesystem          = "npx -y @modelcontextprotocol/server-filesystem D:/golden-wings-reconoganza"
  sequentialthinking  = "npx -y @modelcontextprotocol/server-sequential-thinking"
  puppeteer           = "npx -y @modelcontextprotocol/server-puppeteer"
  "brave-search"      = "npx -y @modelcontextprotocol/server-brave-search"
  time                = "uvx mcp-server-time"
  memory              = "npx -y @modelcontextprotocol/server-memory"
  tavily              = "npx -y tavily-mcp@0.2.3"
  oxylabs             = "uvx oxylabs-mcp"
  exa                 = "npx -y exa-mcp-server"
  playwright          = "npx -y @playwright/mcp@latest --browser=chromium --headless=true --viewport-size=1280x800"
}

foreach ($server in $mcpServers.GetEnumerator()) {
    $name = $server.Key
    $cmdLine = $server.Value
    Write-Host "Starting $name..."
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c $cmdLine" -NoNewWindow
}
