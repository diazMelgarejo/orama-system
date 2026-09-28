// Ambient process.env for vite.config.ts. Keeps `tsc -b` working without
// a separate @types/node install; vite.config.ts only reads PORTAL_URL.
declare const process: {
  env: Record<string, string | undefined>;
};
