import { serve } from "bun";
import index from "./index.html";

const server = serve({
  routes: {
    // Proxy API requests to FastAPI backend
    "/api/*": async (req) => {
      const url = new URL(req.url);
      const backendUrl = `http://localhost:8000${url.pathname}${url.search}`;
      
      return fetch(backendUrl, {
        method: req.method,
        headers: req.headers,
        body: req.body,
      });
    },

    // Proxy static files from FastAPI backend
    "/static/*": async (req) => {
      const url = new URL(req.url);
      const backendUrl = `http://localhost:8000${url.pathname}${url.search}`;
      return fetch(backendUrl);
    },

    // Serve index.html for all unmatched routes.
    "/*": index,
  },

  development: process.env.NODE_ENV !== "production" && {
    // Enable browser hot reloading in development
    hmr: true,

    // Echo console logs from the browser to the server
    console: true,
  },
});

console.log(`🚀 Server running at ${server.url}`);
