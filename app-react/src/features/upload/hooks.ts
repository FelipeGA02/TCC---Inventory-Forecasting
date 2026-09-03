import { useCallback, useRef, useState } from "react";
import { mensagemDoErro } from "@/lib/http/errors";
import { formatarTamanhoArquivo } from "@/lib/format";
import { dispararRetrain, enviarPlanilha, validarArquivo, type ResultadoUpload } from "./api";

export type EtapaUpload = "escolher" | "enviando" | "calculando" | "concluido" | "erro";

export const ETAPAS: { etapa: EtapaUpload; label: string }[] = [
  { etapa: "escolher", label: "Enviar arquivo" },
  { etapa: "enviando", label: "Verificando" },
  { etapa: "calculando", label: "Calculando" },
  { etapa: "concluido", label: "Pronto!" },
];

export interface ArquivoEscolhido {
  nome: string;
  tamanho: string;
}

export function useUploadPlanilha() {
  const [etapa, setEtapa] = useState<EtapaUpload>("escolher");
  const [arquivo, setArquivo] = useState<ArquivoEscolhido | null>(null);
  const [resultado, setResultado] = useState<ResultadoUpload | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const reiniciar = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setEtapa("escolher");
    setArquivo(null);
    setResultado(null);
    setErro(null);
  }, []);

  const enviar = useCallback(async (selecionado: File) => {
    const problema = validarArquivo(selecionado);
    if (problema) {
      setArquivo({ nome: selecionado.name, tamanho: formatarTamanhoArquivo(selecionado.size) });
      setErro(problema);
      setEtapa("erro");
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;

    setArquivo({ nome: selecionado.name, tamanho: formatarTamanhoArquivo(selecionado.size) });
    setErro(null);
    setEtapa("enviando");

    try {
      const enviado = await enviarPlanilha(selecionado, controller.signal);
      setResultado(enviado);

      if (enviado.duplicado) {
        setEtapa("concluido");
        return;
      }

      setEtapa("calculando");
      await dispararRetrain(controller.signal);
      setEtapa("concluido");
    } catch (causa) {
      if (causa instanceof DOMException && causa.name === "AbortError") return;
      setErro(mensagemDoErro(causa));
      setEtapa("erro");
    } finally {
      controllerRef.current = null;
    }
  }, []);

  return { etapa, arquivo, resultado, erro, enviar, reiniciar };
}
