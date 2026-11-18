// Cloudflare Worker: fires the GitHub "Collect" workflow on a reliable schedule (see ADR-003).
// It only presses the button (workflow_dispatch); the collector itself is unchanged.

const REQUIRED = ["GITHUB_OWNER", "GITHUB_REPO", "WORKFLOW_FILE", "GITHUB_REF", "GH_DISPATCH_TOKEN"];

/** Build the GitHub API request. Pure function, so it can be tested without the network. */
export function buildDispatchRequest(env) {
  const missing = REQUIRED.filter((name) => !env[name]);
  if (missing.length > 0) {
    throw new Error(`Missing config: ${missing.join(", ")}`);
  }
  const url =
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}` +
    `/actions/workflows/${env.WORKFLOW_FILE}/dispatches`;
  const init = {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "bike-or-bust-trigger", // GitHub rejects requests without a User-Agent
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: env.GITHUB_REF }),
  };
  return { url, init };
}

/** Send the dispatch. GitHub answers 204 on success; anything else is an error (no retry here). */
export async function dispatch(env, fetchFn = fetch) {
  const { url, init } = buildDispatchRequest(env);
  const response = await fetchFn(url, init);
  if (response.status !== 204) {
    const detail = (await response.text()).slice(0, 200);
    throw new Error(`GitHub dispatch failed: HTTP ${response.status} ${detail}`);
  }
  return response.status;
}

export default {
  async scheduled(controller, env) {
    await dispatch(env);
    console.log(`dispatched ${env.WORKFLOW_FILE} at ${new Date(controller.scheduledTime).toISOString()}`);
  },
};
