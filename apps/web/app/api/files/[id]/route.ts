import { BACKEND_URL } from "@/lib/constants";
import { NextRequest } from "next/server";

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const sessionId = req.nextUrl.searchParams.get("session_id") || "";
  const requestId = crypto.randomUUID().slice(0, 8);

  const backendResponse = await fetch(
    `${BACKEND_URL}/api/files/${id}?session_id=${sessionId}`,
    {
      method: "DELETE",
      headers: { "X-Request-ID": requestId },
    }
  );

  const data = await backendResponse.json();
  return Response.json(data, { status: backendResponse.status });
}
