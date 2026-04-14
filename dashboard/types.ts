export interface ServiceConfig {
  id: string
  name: string
  description: string
  hostUrl: string
  healthUrl: string
}

export interface ServiceStatus {
  online: boolean
  latencyMs: number
}

export interface MCPServerConfig {
  id: string
  name: string
  description: string
  port: number
  healthUrl: string
  openwebuiUrl: string
  displayUrl: string
}

export interface OllamaModelDetails {
  format: string
  family: string
  families: string[]
  parameter_size: string
  quantization_level: string
}

export interface OllamaModel {
  name: string
  model: string
  modified_at: string
  size: number
  digest: string
  details: OllamaModelDetails
}

export interface OllamaTagsResponse {
  models: OllamaModel[]
}

export interface MLXModel {
  id: string
  object: string
  created: number
}

export interface MLXModelsResponse {
  object: string
  data: MLXModel[]
}
