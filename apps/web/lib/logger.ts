const isDev = process.env.NODE_ENV === "development";

export function log(event: string, data?: Record<string, unknown>) {
  if (isDev) console.log(`[${event}]`, data ?? "");
}
