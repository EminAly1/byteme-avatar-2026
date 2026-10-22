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
