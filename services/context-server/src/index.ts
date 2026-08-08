import { createSchema, createYoga } from 'graphql-yoga';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { createServer, type IncomingMessage } from 'node:http';
import { typeDefs } from './schema.js';
import { resolvers } from './resolvers.js';
import { createContextMcpServer } from './mcp-server.js';

const PORT = Number(process.env.CONTEXT_PORT ?? 4000);
const API_KEY = process.env.CONTEXT_API_KEY;
const MAX_MCP_BODY_BYTES = 1_048_576;

const yoga = createYoga({
  schema: createSchema({ typeDefs, resolvers }),
  graphiql: process.env.NODE_ENV !== 'production',
  landingPage: process.env.NODE_ENV !== 'production',
});

async function readMcpRequestBody(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += bytes.length;
    if (size > MAX_MCP_BODY_BYTES) throw new Error('MCP request exceeds 1 MiB');
    chunks.push(bytes);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf-8'));
}

const server = createServer(async (request, response) => {
  const { pathname } = new URL(request.url ?? '/', 'http://localhost');
  if (process.env.NODE_ENV === 'production' && !API_KEY) {
    response.writeHead(503).end('CONTEXT_API_KEY is required in production');
    return;
  }
  if (API_KEY && request.headers.authorization !== `Bearer ${API_KEY}`) {
    response.writeHead(401, { 'WWW-Authenticate': 'Bearer' }).end('Unauthorized');
    return;
  }
  if (pathname !== '/mcp') {
    await yoga(request, response);
    return;
  }

  try {
    const body = request.method === 'POST' ? await readMcpRequestBody(request) : undefined;
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    await createContextMcpServer().connect(transport);
    await transport.handleRequest(request, response, body);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Invalid MCP request';
    response.writeHead(400).end(message);
  }
});

server.listen(PORT, () => {
  console.log(`[context-server] GraphQL: http://localhost:${PORT}/graphql`);
  console.log(`[context-server] MCP: http://localhost:${PORT}/mcp`);
});
