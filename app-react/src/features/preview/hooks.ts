import { useMemo, useState } from "react";
import { useQuery } from "@/lib/query/useQuery";
import type { RegistroImportado } from "@/domain/types";
import { buscarRegistrosImportados } from "./api";

export interface FiltrosPreview {
  produto: string;
  unidade: string;
  busca: string;
}

export const filtrosVazios: FiltrosPreview = { produto: "todos", unidade: "todos", busca: "" };

const POR_PAGINA = 10;

export function useRegistrosImportados(filtros: FiltrosPreview) {
  const { data, carregando, erro, recarregar } = useQuery(
    (signal) => buscarRegistrosImportados(signal),
    [],
  );
  const [pagina, setPagina] = useState(1);

  const filtrados = useMemo<RegistroImportado[]>(() => {
    const registros = data ?? [];
    const busca = filtros.busca.trim().toLowerCase();

    return registros.filter(
      (registro) =>
        (filtros.produto === "todos" || registro.produto === filtros.produto) &&
        (filtros.unidade === "todos" || registro.unidade === filtros.unidade) &&
        (busca === "" ||
          registro.produto.toLowerCase().includes(busca) ||
          registro.unidade.toLowerCase().includes(busca) ||
          registro.data.includes(busca)),
    );
  }, [data, filtros.produto, filtros.unidade, filtros.busca]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / POR_PAGINA));
  const paginaAtual = Math.min(pagina, totalPaginas);
  const inicio = (paginaAtual - 1) * POR_PAGINA;

  return {
    carregando,
    erro,
    recarregar,
    registros: filtrados.slice(inicio, inicio + POR_PAGINA),
    total: filtrados.length,
    pagina: paginaAtual,
    totalPaginas,
    porPagina: POR_PAGINA,
    irPara: setPagina,
  };
}
