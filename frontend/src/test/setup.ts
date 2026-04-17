import { afterAll, afterEach, beforeAll } from 'vitest'
import { setupServer } from 'msw/node'

/** MSW server instance; individual test files call server.use(...) with handlers. */
export const testServer = setupServer()

beforeAll(() => {
  testServer.listen({ onUnhandledRequest: 'error' })
})

afterEach(() => {
  testServer.resetHandlers()
})

afterAll(() => {
  testServer.close()
})
