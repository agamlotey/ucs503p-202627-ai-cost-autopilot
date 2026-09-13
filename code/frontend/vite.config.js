var _a, _b;
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import checker from 'vite-plugin-checker';
// The gateway the dashboard talks to. Override with GATEWAY_URL if it isn't on
// the default port, e.g.  GATEWAY_URL=http://localhost:8001 npm run dev
// eslint-disable-next-line @typescript-eslint/no-explicit-any
var GATEWAY = ((_b = (_a = globalThis.process) === null || _a === void 0 ? void 0 : _a.env) === null || _b === void 0 ? void 0 : _b.GATEWAY_URL) || 'http://localhost:8000';
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        tsconfigPaths(),
        react(),
        checker({
            typescript: true,
            eslint: {
                lintCommand: 'eslint "./src/**/*.{ts,tsx}"',
            },
        }),
    ],
    preview: {
        port: 5000,
    },
    server: {
        host: '0.0.0.0',
        port: 3000,
        // Forward API calls to the gateway so the browser sees them as same-origin
        // (no CORS needed). The page calls /stats and /v1/chat/completions directly.
        proxy: {
            '/stats': GATEWAY,
            '/v1': GATEWAY,
            '/health': GATEWAY,
        },
    },
    base: '/',
});
