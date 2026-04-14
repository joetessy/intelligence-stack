"use client"

import { useQuery } from "@tanstack/react-query"
import Header from "@/components/Header"
import ServiceCard from "@/components/ServiceCard"
import ModelList from "@/components/ModelList"
import MLXModelList from "@/components/MLXModelList"
import QuickLaunch from "@/components/QuickLaunch"
import { SERVICES } from "@/lib/services"

const Page = () => {
  // A lightweight timer query: the queryFn just returns the current timestamp.
  // TanStack Query refetches it every 10s, which updates dataUpdatedAt —
  // that's what we pass to Header as the "last refreshed" time.
  const { dataUpdatedAt } = useQuery({
    queryKey: ["tick"],
    queryFn: () => Date.now(),
    refetchInterval: 10_000,
    staleTime: 0
  })

  return (
    <main className="min-h-screen px-6 py-10 max-w-5xl mx-auto">
      <Header lastUpdated={dataUpdatedAt} />
      <QuickLaunch />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {SERVICES.map((service, i) => (
          <ServiceCard key={service.id} service={service} animationDelay={i * 70} />
        ))}
      </div>

      <div className="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelList />
        <MLXModelList />
      </div>
    </main>
  )
}

export default Page
