import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createContextMcpServer } from './mcp-server.js';

const transport = new StdioServerTransport();
await createContextMcpServer().connect(transport);
console.error('[startup-context] MCP stdio server ready — 12 tools registered');
