import { useQuery } from "@/lib/query/useQuery";
import { buscarResumo, type ResumoDashboard } from "./api";
import type { QueryResult } from "@/lib/query/useQuery";

export function useResumoDashboard(): QueryResult<ResumoDashboard> {
  return useQuery((signal) => buscarResumo(signal), []);
}
