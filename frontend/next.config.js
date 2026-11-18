const API_URL = process.env.API_URL || 'http://localhost:8000';
const STATIC_EXPORT = process.env.STATIC_EXPORT === '1';

module.exports = STATIC_EXPORT
  ? {
      // Single-service deploy: pages are exported as static files and served by FastAPI.
      reactStrictMode: true,
      output: 'export',
      trailingSlash: true,
      images: { unoptimized: true },
    }
  : {
      reactStrictMode: true,
      async rewrites() {
        return [{ source: '/api/:path*', destination: `${API_URL}/api/:path*` }];
      },
    };
