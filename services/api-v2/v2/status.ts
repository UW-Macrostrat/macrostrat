const larkin = require("./larkin");

function env(key: string): string | null {
  return process.env[key] || null;
}

/** The build this process runs, from the variables CI sets in the image. */
export function versionRoute(req, res) {
  res.set("Cache-Control", "no-store");
  res.json({
    service: "api-v2",
    version: env("MACROSTRAT_VERSION"),
    release: process.env.MACROSTRAT_RELEASE === "true",
    commit: env("MACROSTRAT_COMMIT"),
    build_date: env("MACROSTRAT_BUILD_DATE"),
    repository: env("MACROSTRAT_REPOSITORY"),
  });
}

export async function healthRoute(req, res) {
  res.set("Cache-Control", "no-store");
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error("timed out")), 5000).unref(),
  );
  try {
    await Promise.race([
      larkin.queryPgAsync("macrostrat", "SELECT 1", []),
      timeout,
    ]);
    res.json({ status: "ok" });
  } catch (err) {
    larkin.log("error", `Health check failed: ${err.message}`);
    res.status(503).json({ status: "unavailable" });
  }
}
