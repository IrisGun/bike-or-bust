import assert from "node:assert/strict";
import { test } from "node:test";

import { buildDispatchRequest, dispatch } from "../src/index.js";

const ENV = {
  GITHUB_OWNER: "IrisGun",
  GITHUB_REPO: "bike-or-bust",
  WORKFLOW_FILE: "collect.yml",
  GITHUB_REF: "main",
  GH_DISPATCH_TOKEN: "fake-token",
};

const fakeFetch = (status, body = "") => async () => new Response(status === 204 ? null : body, { status });

test("builds the dispatch URL, headers and body", () => {
  const { url, init } = buildDispatchRequest(ENV);
  assert.equal(
    url,
    "https://api.github.com/repos/IrisGun/bike-or-bust/actions/workflows/collect.yml/dispatches",
  );
  assert.equal(init.method, "POST");
  assert.equal(init.headers.Authorization, "Bearer fake-token");
  assert.ok(init.headers["User-Agent"]);
  assert.deepEqual(JSON.parse(init.body), { ref: "main" });
});

test("fails loudly when config is missing, naming the variable", () => {
  const { GH_DISPATCH_TOKEN, ...incomplete } = ENV;
  assert.throws(() => buildDispatchRequest(incomplete), /GH_DISPATCH_TOKEN/);
});

test("204 is success", async () => {
  assert.equal(await dispatch(ENV, fakeFetch(204)), 204);
});

test("non-204 throws with the status code", async () => {
  await assert.rejects(dispatch(ENV, fakeFetch(401, "Bad credentials")), /HTTP 401 Bad credentials/);
});

test("the token never appears in the error message", async () => {
  await assert.rejects(dispatch(ENV, fakeFetch(403, "Forbidden")), (err) => !err.message.includes("fake-token"));
});
