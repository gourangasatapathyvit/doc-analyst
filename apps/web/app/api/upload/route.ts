import { BACKEND_URL } from "@/lib/constants";
import { NextRequest } from "next/server";

// Increase body size limit for file uploads (default is 1MB)
export const config = {
  api: { bodyParser: false },
};

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const requestId = crypto.randomUUID().slice(0, 8);

  const backendResponse = await fetch(`${BACKEND_URL}/api/upload`, {
    method: "POST",
    headers: { "X-Request-ID": requestId },
    body: formData,
  });

  const data = await backendResponse.json();
  return Response.json(data, { status: backendResponse.status });
}
