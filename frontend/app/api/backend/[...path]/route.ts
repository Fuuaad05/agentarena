// Browser -> same-origin proxy -> Docker host. Credentials never enter the browser bundle.
export const maxDuration = 300;
const allowed =
  /^api\/(health|scenarios|investigations(?:\/\d+)?|investigate(?:\/stream)?)$/;
async function proxy(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const endpoint = path.join("/");
  if (!allowed.test(endpoint))
    return Response.json({ detail: "Unknown endpoint" }, { status: 404 });
  if (request.method === "POST" && !endpoint.startsWith("api/investigate"))
    return new Response(null, { status: 405 });
  if (
    request.method === "GET" &&
    endpoint.startsWith("api/investigate") &&
    !endpoint.startsWith("api/investigations")
  )
    return new Response(null, { status: 405 });
  const origin =
    process.env.BACKEND_URL ||
    (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");
  if (!origin)
    return Response.json(
      {
        detail:
          "Live backend is not configured. Open the recorded investigation instead.",
      },
      { status: 503 },
    );
  try {
    const url = new URL(endpoint, origin.replace(/\/+$/, "") + "/");
    if (process.env.NODE_ENV === "production" && url.protocol !== "https:")
      return Response.json(
        { detail: "Backend must use HTTPS." },
        { status: 503 },
      );
    const response = await fetch(url, {
      method: request.method,
      cache: "no-store",
      redirect: "error",
      headers: {
        "Content-Type": "application/json",
        "X-Arena-Token": process.env.AGENTARENA_API_TOKEN || "",
      },
      body: request.method === "POST" ? await request.text() : undefined,
      signal: AbortSignal.timeout(request.method === "POST" ? 290000 : 25000),
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") || "application/json",
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return Response.json(
      {
        detail:
          "Live backend unavailable. Recorded evidence is still available.",
      },
      { status: 502 },
    );
  }
}
export { proxy as GET, proxy as POST };
