import { useQuery } from "@tanstack/react-query";
import { all } from "./api";
import type { Product, Party, Location, Lot } from "./types";

export const useRecords = <T>(path: string) =>
  useQuery({
    queryKey: ["records", path],
    queryFn: ({ signal }) => all<T>(path, signal),
    staleTime: 15000,
    retry: false,
  });
export function useCatalog() {
  const products = useRecords<Product>("/products"),
    parties = useRecords<Party>("/parties"),
    locations = useRecords<Location>("/locations"),
    lots = useRecords<Lot>("/lots");
  return {
    products: products.data || [],
    parties: parties.data || [],
    locations: locations.data || [],
    lots: lots.data || [],
    loading: [products, parties, locations, lots].some((x) => x.isPending),
    error: [products, parties, locations, lots].find((x) => x.isError)?.error,
  };
}

export function useRecordDetails<T>(path: string, ids: string[] | undefined) {
  return useQuery({
    queryKey: ["record-details", path, ids],
    queryFn: async ({ signal }) => {
      const { request } = await import("./api");
      const results: T[] = [];
      // Complete the prototype's list without flooding the local API/DB pool.
      for (let i = 0; i < (ids?.length || 0); i += 4) {
        results.push(
          ...(await Promise.all(
            ids!
              .slice(i, i + 4)
              .map((id) => request<T>(path + "/" + id, { signal })),
          )),
        );
      }
      return results;
    },
    enabled: ids !== undefined,
    retry: false,
    staleTime: 15000,
  });
}
