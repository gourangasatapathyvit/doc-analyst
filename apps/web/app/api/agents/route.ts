import { BACKEND_URL } from "@/lib/constants";

export async function GET() {
  const res = await fetch(`${BACKEND_URL}/api/agents`);
  const data = await res.json();
  return Response.json(data, { status: res.status });
}
