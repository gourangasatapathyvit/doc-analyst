import { BACKEND_URL } from "@/lib/constants";

interface ToolCall {
  tool: string;
  agent: string;
  input: string;
  output: string;
}

export async function POST(req: Request) {
  const body = await req.json();
  const requestId = crypto.randomUUID().slice(0, 8);

  // Read session/file context from request headers or body
  const sessionId = req.headers.get("x-session-id") || body.session_id || "";
  const fileIdsHeader = req.headers.get("x-file-ids") || "";
  const fileIds = fileIdsHeader
    ? fileIdsHeader.split(",").filter(Boolean)
    : body.file_ids || [];

  // AI SDK v6: messages use `parts` array
  const lastMessage = body.messages?.at(-1);
  let messageText = "";
  if (lastMessage) {
    if (Array.isArray(lastMessage.parts)) {
      messageText = lastMessage.parts
        .filter((p: { type: string }) => p.type === "text")
        .map((p: { text: string }) => p.text)
        .join("");
    } else if (typeof lastMessage.content === "string") {
      messageText = lastMessage.content;
    }
  }

  const backendResponse = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": requestId,
      "X-Session-ID": sessionId,
    },
    body: JSON.stringify({
      message: messageText,
      session_id: sessionId,
      file_ids: fileIds,
    }),
  });

  if (!backendResponse.ok) {
    return new Response("Backend error", { status: backendResponse.status });
  }

  const reader = backendResponse.body?.getReader();
  if (!reader) {
    return new Response("No response body", { status: 500 });
  }

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  // Collect tool calls and agents, stream only clean text
  const toolCalls: ToolCall[] = [];
  const agents: string[] = [];
  const pendingTools: Map<string, Partial<ToolCall>> = new Map();

  const stream = new ReadableStream({
    async start(controller) {
      let buffer = "";
      let eventType = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const dataStr = line.slice(6).trim();
              try {
                const data = JSON.parse(dataStr);

                if (eventType === "token" && data.content) {
                  // Only text tokens go to the stream
                  controller.enqueue(encoder.encode(data.content));
                } else if (eventType === "agent_start") {
                  if (!agents.includes(data.agent)) {
                    agents.push(data.agent);
                  }
                } else if (eventType === "tool_start") {
                  pendingTools.set(data.tool, {
                    tool: data.tool,
                    agent: data.agent,
                    input: data.input || "",
                  });
                } else if (eventType === "tool_end") {
                  const pending = pendingTools.get(data.tool);
                  toolCalls.push({
                    tool: data.tool,
                    agent: data.agent,
                    input: pending?.input || "",
                    output: data.output || "",
                  });
                  pendingTools.delete(data.tool);
                } else if (eventType === "error") {
                  controller.enqueue(
                    encoder.encode(`\n\n**Error:** ${data.message}`)
                  );
                }
              } catch {
                // skip malformed JSON
              }
              eventType = "";
            }
          }
        }

        // After stream ends, append tool trace as a JSON block
        if (toolCalls.length > 0 || agents.length > 0) {
          const traceJson = JSON.stringify({ toolCalls, agents });
          controller.enqueue(
            encoder.encode(`\n\n<!--TRACE:${traceJson}-->`)
          );
        }
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "X-Request-ID": requestId,
    },
  });
}
