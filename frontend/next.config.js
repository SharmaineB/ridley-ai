const API_URL = process.env.API_URL || 'http://localhost:8000';

module.exports = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${API_URL}/api/:path*` }];
  },
};
