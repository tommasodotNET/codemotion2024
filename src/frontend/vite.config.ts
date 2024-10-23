import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default () => {
  process.env = {...process.env, ...loadEnv('', process.cwd())};

  // import.meta.env.VITE_NAME available here with: process.env.VITE_NAME
  // import.meta.env.VITE_PORT available here with: process.env.VITE_PORT

  return defineConfig({
    plugins: [react()],
    assetsInclude: ['**/*.md'],
    server: {
      proxy: {
        '/api': {
          target: process.env.services__api__http__0,
        },
      },
    },
  });
}

// https://vitejs.dev/config/
// export default defineConfig({
//   process.env = loadEnv('', process.cwd());

//   plugins: [react()],
//   assetsInclude: ['**/*.md'],
//   server: {
//     proxy: {
//       '/api': {
//         target: ,
//       },
//     },
//   },
// });
