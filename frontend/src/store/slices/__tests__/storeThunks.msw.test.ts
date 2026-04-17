import { combineReducers, configureStore } from '@reduxjs/toolkit'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { testServer } from '@/test/setup'
import authReducer from '../authSlice'
import storeReducer, {
  fetchStoreBooks,
  normalizeStoreBook,
  purchaseBook,
  storeInitialState,
} from '../storeSlice'

function createStore(preloaded?: {
  store?: Partial<typeof storeInitialState>
  auth?: Partial<import('../authSlice').AuthState>
}) {
  return configureStore({
    reducer: combineReducers({ auth: authReducer, store: storeReducer }),
    preloadedState: {
      auth: {
        isAuthenticated: true,
        user: { id: 'user-1', email: 'a@b.com', first_name: 'Test' },
        token: 'tok',
        refreshToken: null,
        loading: false,
        error: null,
        ...preloaded?.auth,
      },
      store: {
        ...storeInitialState,
        lastFetched: null,
        ...preloaded?.store,
      },
    },
  })
}

describe('fetchStoreBooks (MSW)', () => {
  it('loads catalog and list endpoints into the store', async () => {
    const apiBook = {
      id: 'bk-1',
      title: 'Hello',
      author: 'World',
      description: 'D',
      price: 9.99,
      credits: 1,
      duration: 100,
      narrator: 'N',
      published_year: 2020,
      genre: 'G',
      rating: 4,
      review_count: 2,
      chapters: [],
    }

    testServer.use(
      http.get('*/backend/store/catalog', () => HttpResponse.json({ books: [apiBook], total: 1 })),
      http.get('*/backend/store/featured', () => HttpResponse.json({ books: [apiBook], total: 1 })),
      http.get('*/backend/store/new-releases', () => HttpResponse.json({ books: [], total: 0 })),
      http.get('*/backend/store/bestsellers', () => HttpResponse.json({ books: [], total: 0 })),
    )

    const store = createStore()
    await store.dispatch(fetchStoreBooks())

    const st = store.getState().store
    expect(st.loading).toBe(false)
    expect(st.bookIds).toContain('bk-1')
    expect(st.books['bk-1'].title).toBe('Hello')
    expect(st.books['bk-1'].price).toBe(999)
    expect(st.featuredBookIds).toContain('bk-1')
  })
})

describe('purchaseBook (MSW)', () => {
  it('deducts credits after pay-with-credits and store purchase', async () => {
    const book = normalizeStoreBook({
      id: 'book-1',
      title: 'Buy Me',
      author: 'Seller',
      description: '',
      price: 12.99,
      credits: 2,
      duration: 1,
      narrator: '',
      published_year: 2020,
      genre: '',
      rating: 0,
      review_count: 0,
      chapters: [],
    })

    testServer.use(
      http.post('*/payment/pay-with-credits', async () =>
        HttpResponse.json({
          payment_id: 'p1',
          order_id: 'o1',
          credits_deducted: 2,
          remaining_credits: 3,
          status: 'ok',
          message: 'ok',
        }),
      ),
      http.post('*/backend/store/purchase', async () => HttpResponse.json({ ok: true })),
    )

    const store = createStore({
      store: {
        books: { 'book-1': book },
        bookIds: ['book-1'],
        userCredits: 10,
      },
    })

    const result = await store.dispatch(
      purchaseBook({ bookId: 'book-1', useCredits: true }),
    )

    expect(result.type.endsWith('/fulfilled')).toBe(true)
    expect(store.getState().store.userCredits).toBe(8)
  })
})
