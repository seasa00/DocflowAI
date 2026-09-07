export async function POST(request: Request) {
  const body = await request.formData();
  const apiUrl = process.env.API_URL ?? "http://localhost:8000";
  try {
    const upstream = await fetch(`${apiUrl}/documents`, { method: "POST", body });
    return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" } });
  } catch {
    return Response.json({ detail: "The document API is unavailable. Check that the API service is running." }, { status: 503 });
  }
}
