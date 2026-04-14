import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import ServiceCard from "./ServiceCard"
import type { ServiceConfig } from "@/types"

const mockService: ServiceConfig = {
  id: "test-service",
  name: "Test Service",
  description: "A test service",
  hostUrl: "http://localhost:9999",
  healthUrl: "http://localhost:9999"
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } }
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe("ServiceCard", () => {
  beforeEach(() => {
    // Never resolves so we test the loading/initial state
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() => new Promise(() => {}))
    )
  })

  it("renders the service name", () => {
    render(<ServiceCard service={mockService} />, { wrapper: createWrapper() })
    expect(screen.getByText("Test Service")).toBeInTheDocument()
  })

  it("renders the service description", () => {
    render(<ServiceCard service={mockService} />, { wrapper: createWrapper() })
    expect(screen.getByText("A test service")).toBeInTheDocument()
  })

  it("shows Checking state before data loads", () => {
    render(<ServiceCard service={mockService} />, { wrapper: createWrapper() })
    expect(screen.getByText("Checking")).toBeInTheDocument()
  })

  it("renders the host URL as a link", () => {
    render(<ServiceCard service={mockService} />, { wrapper: createWrapper() })
    const link = screen.getByRole("link")
    expect(link).toHaveAttribute("href", "http://localhost:9999")
  })

  it("link opens in a new tab", () => {
    render(<ServiceCard service={mockService} />, { wrapper: createWrapper() })
    const link = screen.getByRole("link")
    expect(link).toHaveAttribute("target", "_blank")
  })
})
