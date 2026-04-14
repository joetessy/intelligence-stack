import { describe, it, expect } from "vitest"
import { formatBytes } from "./formatBytes"

describe("formatBytes", () => {
  it('returns "0 B" for 0 bytes', () => {
    expect(formatBytes({ bytes: 0 })).toBe("0 B")
  })

  it("formats sub-kilobyte values as bytes", () => {
    expect(formatBytes({ bytes: 512 })).toBe("512 B")
  })

  it("formats kilobytes", () => {
    expect(formatBytes({ bytes: 1024 })).toBe("1 KB")
  })

  it("formats megabytes", () => {
    expect(formatBytes({ bytes: 1024 * 1024 })).toBe("1 MB")
  })

  it("formats gigabytes", () => {
    expect(formatBytes({ bytes: 1024 * 1024 * 1024 })).toBe("1 GB")
  })

  it("formats terabytes", () => {
    expect(formatBytes({ bytes: 1024 * 1024 * 1024 * 1024 })).toBe("1 TB")
  })

  it("rounds to 1 decimal by default", () => {
    expect(formatBytes({ bytes: 1536 })).toBe("1.5 KB")
  })

  it("respects custom decimals (parseFloat trims trailing zeros)", () => {
    // parseFloat removes trailing zeros: 1.50 → 1.5
    expect(formatBytes({ bytes: 1536, decimals: 2 })).toBe("1.5 KB")
  })

  it("formats large model sizes correctly", () => {
    // ~20 GB model
    const twentyGb = 20 * 1024 * 1024 * 1024
    expect(formatBytes({ bytes: twentyGb })).toBe("20 GB")
  })
})
