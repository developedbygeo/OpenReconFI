import { defineConfig } from 'orval'

export default defineConfig({
  openreconfi: {
    input: '../openapi.json',
    output: {
      mode: 'tags-split',
      target: 'src/api',
      schemas: 'src/api/types',
      client: 'zod',
    },
  },
})
