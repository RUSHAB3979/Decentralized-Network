export const config = {
  port: Number(process.env.PORT ?? 8080),
  providerTtlMs: Number(process.env.PROVIDER_TTL_MS ?? 120_000)
};
