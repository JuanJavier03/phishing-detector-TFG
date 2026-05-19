"use client";

import { useEffect, useRef, useState } from "react";

type PollingOptions<T> = {
  pauseWhenHidden?: boolean;
  shouldPoll?: (data: T | null) => boolean;
  pollKey?: string;
};

type QueryState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
};

export function usePollingQuery<T>(
  loader: () => Promise<T>,
  dependencyKey: string,
  intervalMs = 4000,
  enabled = true,
  options: PollingOptions<T> = {},
): QueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  const shouldPollRef = useRef<(data: T | null) => boolean>(() => true);
  const dataRef = useRef<T | null>(null);
  const inFlightRef = useRef(false);
  const pauseWhenHidden = options.pauseWhenHidden ?? true;
  const pollKey = options.pollKey ?? "";
  const [isDocumentVisible, setIsDocumentVisible] = useState(() =>
    typeof document === "undefined" ? true : document.visibilityState === "visible",
  );

  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  useEffect(() => {
    shouldPollRef.current = options.shouldPoll ?? (() => true);
  }, [options.shouldPoll]);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }

    function handleVisibilityChange() {
      setIsDocumentVisible(document.visibilityState === "visible");
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  async function run() {
    if (inFlightRef.current) {
      return dataRef.current;
    }

    inFlightRef.current = true;
    try {
      const next = await loaderRef.current();
      dataRef.current = next;
      setData(next);
      setError(null);
      return next;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
      return dataRef.current;
    } finally {
      inFlightRef.current = false;
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    if (pauseWhenHidden && !isDocumentVisible) {
      setLoading(false);
      return;
    }

    let active = true;
    let timer: number | null = null;

    const scheduleNextRun = () => {
      if (!active) {
        return;
      }
      if (!shouldPollRef.current(dataRef.current)) {
        return;
      }
      timer = window.setTimeout(() => {
        void tick();
      }, intervalMs);
    };

    const tick = async () => {
      if (!active) {
        return;
      }
      await run();
      scheduleNextRun();
    };

    setLoading(true);
    void tick();

    return () => {
      active = false;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [
    dependencyKey,
    enabled,
    intervalMs,
    isDocumentVisible,
    pauseWhenHidden,
    pollKey,
  ]);

  return {
    data,
    error,
    loading,
    refresh: async () => {
      await run();
    },
  };
}
