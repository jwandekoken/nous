// Base DTOs
export interface IdentifierDto {
  value: string;
  type: string;
}

export interface EntityDto {
  id: string; // UUID is a string in TS
  created_at: string; // ISO date string
  metadata?: Record<string, string> | null;
}

export interface FactDto {
  name: string;
  type: string;
  fact_id?: string | null;
}

export interface SourceDto {
  id: string; // UUID
  content: string;
  timestamp: string; // ISO date string
}

export interface HasFactDto {
  verb: string;
  confidence_score: number;
  created_at: string; // ISO date string
}

// Request Payloads
export interface AssimilateKnowledgeRequest {
  identifier: IdentifierDto;
  content: string;
  timestamp?: string | null; // ISO date string
  history?: string[] | null;
}

// API Responses
export interface AssimilatedFactDto {
  fact: FactDto;
  relationship: HasFactDto;
}

export interface AssimilateKnowledgeResponse {
  entity: EntityDto;
  source: SourceDto;
  assimilated_facts: AssimilatedFactDto[];
}

export interface HasIdentifierDto {
  is_primary: boolean;
  created_at: string; // ISO date string
}

export interface IdentifierWithRelationshipDto {
  identifier: IdentifierDto;
  relationship: HasIdentifierDto;
}

export interface FactWithSourceDto {
  fact: FactDto;
  relationship: HasFactDto;
  source?: SourceDto | null;
}

export interface GetEntityResponse {
  entity: EntityDto;
  identifier: IdentifierWithRelationshipDto;
  facts: FactWithSourceDto[];
}
