import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import ModelList from "./ModelList"

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe("ModelList", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
  })

  it("shows loading state before data resolves", () => {
    vi.mocked(global.fetch).mockImplementation(() => new Promise(() => {}))
    render(<ModelList />, { wrapper: createWrapper() })
    expect(screen.getByText(/Loading models/i)).toBeInTheDocument()
  })

  it("renders model names after data loads", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        models: [
          {
            name: "llama3.2:3b",
            model: "llama3.2:3b",
            size: 2_000_000_000,
            modified_at: "",
            digest: "",
            details: {
              format: "gguf",
              family: "llama",
              families: ["llama"],
              parameter_size: "3B",
              quantization_level: "Q4_K_M"
            }
          }
        ]
      })
    } as Response)

    render(<ModelList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText("llama3.2:3b")).toBeInTheDocument()
    })
  })

  it("renders model family and parameter size", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        models: [
          {
            name: "gemma3:12b",
            model: "gemma3:12b",
            size: 8_000_000_000,
            modified_at: "",
            digest: "",
            details: {
              format: "gguf",
              family: "gemma3",
              families: ["gemma3"],
              parameter_size: "12B",
              quantization_level: "Q4_K_M"
            }
          }
        ]
      })
    } as Response)

    render(<ModelList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText("gemma3")).toBeInTheDocument()
      expect(screen.getByText("12B")).toBeInTheDocument()
    })
  })

  it("shows empty state when no models are returned", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ models: [] })
    } as Response)

    render(<ModelList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText(/Ollama offline or no models pulled/i)).toBeInTheDocument()
    })
  })

  it("shows formatted size", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        models: [
          {
            name: "test:model",
            model: "test:model",
            size: 1024 * 1024 * 1024, // 1 GB
            modified_at: "",
            digest: "",
            details: {
              format: "gguf",
              family: "test",
              families: [],
              parameter_size: "1B",
              quantization_level: ""
            }
          }
        ]
      })
    } as Response)

    render(<ModelList />, { wrapper: createWrapper() })
    await waitFor(() => {
      expect(screen.getByText("1 GB")).toBeInTheDocument()
    })
  })
})
