// One review call through the Vercel AI Gateway, driven by ../run_gateway_review.py.
// Reads {model, system, user, parameters} as JSON on stdin and writes the complete result
// to stdout: every step's content verbatim (reasoning text, gateway tool calls and their raw
// results, text), the response, provider metadata (serving provider, build, cost) and usage.
// The gateway executes the search and fetch tools itself and returns their raw output
// here, so every source the model saw is recorded (Constitutional Rule 13).
import { generateText, stepCountIs } from 'ai';
import { gateway } from '@ai-sdk/gateway';

const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const request = JSON.parse(Buffer.concat(chunks).toString('utf8'));
const p = request.parameters;

try {
  const result = await generateText({
    model: gateway(request.model),
    system: request.system,
    prompt: request.user,
    maxOutputTokens: p.maxOutputTokens,
    reasoning: p.reasoning,
    providerOptions: p.providerOptions,
    tools: {
      perplexity_search: gateway.tools.perplexitySearch(p.tools.perplexity_search),
      browserbase_fetch: gateway.tools.browserbaseFetch(p.tools.browserbase_fetch),
    },
    stopWhen: stepCountIs(p.maxSteps),
  });
  process.stdout.write(JSON.stringify({
    steps: result.steps,
    response: result.response,
    providerMetadata: result.providerMetadata,
    totalUsage: result.totalUsage,
    finishReason: result.finishReason,
  }));
} catch (err) {
  // Report the provider's error, with its body, to the driver, which records it and stops.
  process.stdout.write(JSON.stringify({
    error: {
      name: err?.name, message: err?.message, statusCode: err?.statusCode,
      responseBody: err?.responseBody, cause: String(err?.cause ?? ''),
    },
  }));
  process.exitCode = 1;
}
