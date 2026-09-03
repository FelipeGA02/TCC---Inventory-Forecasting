import { useQuery, useMutation } from "@/lib/query/useQuery";
import { buscarHistorico, exportarRelatorio, type ParametrosExportacao } from "./api";

export function useHistoricoRelatorios() {
  return useQuery((signal) => buscarHistorico(signal), []);
}

export function useExportacao() {
  return useMutation((parametros: ParametrosExportacao) => exportarRelatorio(parametros));
}
