/**
 * Typed Redux Hooks
 * 
 * Pre-typed versions of useDispatch and useSelector hooks.
 * Use these throughout the application instead of plain redux hooks.
 * 
 * @example
 * // In a component:
 * import { useAppDispatch, useAppSelector } from '@/store'
 * 
 * const dispatch = useAppDispatch()
 * const user = useAppSelector(selectCurrentUser)
 */

import { useDispatch, useSelector } from 'react-redux'
import type { TypedUseSelectorHook } from 'react-redux'
import type { RootState, AppDispatch } from './index'

// Typed dispatch hook - use this instead of plain useDispatch
export const useAppDispatch: () => AppDispatch = useDispatch

// Typed selector hook - use this instead of plain useSelector
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector
