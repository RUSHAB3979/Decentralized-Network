import type {
  ComputeJobSubmit,
  ProviderHeartbeat
} from "../../../packages/contracts/src/index.js";

export interface ProviderRecord extends ProviderHeartbeat {
  lastSeenEpochMs: number;
}

export interface ComputeJobRecord {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  createdAt: string;
  providerId?: string;
  request: ComputeJobSubmit;
}

export const providers = new Map<string, ProviderRecord>();
export const jobs = new Map<string, ComputeJobRecord>();
