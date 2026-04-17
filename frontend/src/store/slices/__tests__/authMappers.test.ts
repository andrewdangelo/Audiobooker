import { describe, expect, it } from 'vitest'
import { getUserDisplayName, type AuthUser } from '../authSlice'

describe('getUserDisplayName', () => {
  it('returns User when null', () => {
    expect(getUserDisplayName(null)).toBe('User')
  })

  it('prefers first and last name', () => {
    const user: AuthUser = {
      id: '1',
      email: 'a@b.com',
      first_name: 'Ada',
      last_name: 'Lovelace',
    }
    expect(getUserDisplayName(user)).toBe('Ada Lovelace')
  })

  it('falls back to first_name only', () => {
    const user: AuthUser = {
      id: '1',
      email: 'a@b.com',
      first_name: 'Ada',
    }
    expect(getUserDisplayName(user)).toBe('Ada')
  })

  it('falls back to username when first_name missing', () => {
    const user: AuthUser = {
      id: '1',
      email: 'a@b.com',
      first_name: '',
      username: 'adal',
    }
    expect(getUserDisplayName(user)).toBe('adal')
  })

  it('falls back to email local part', () => {
    const user: AuthUser = {
      id: '1',
      email: 'reader@example.com',
      first_name: '',
    }
    expect(getUserDisplayName(user)).toBe('reader')
  })
})
