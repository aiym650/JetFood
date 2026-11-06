export type ApiListResponse<T> = T[] | { results: T[]; [key: string]: unknown };

export function getApiListResults<T>(response: ApiListResponse<T>): T[] {
  return Array.isArray(response) ? response : response.results;
}
